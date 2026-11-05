#!/usr/bin/env python3
"""Collect and analyze one model's self-reported answer-correctness probabilities.

The exact Chinese prompt is embedded below. The ``collect`` command sends
only the question, question type, and the model's previous answer. The
``analyze`` command joins saved replies to the gold answers and writes
question-level, model-level, and ten-bin CSV results. Blank or failed
original answers and invalid, failed, or truncated probability replies are
excluded from the analysis. No figure is produced.

Without ``--execute``, collection previews a request without calling an API.
Dependencies: Python 3.10+ and openpyxl.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from statistics import mean
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from openpyxl import load_workbook

WORKBOOK_NAME = "hydrobench_final_model_answer_table.xlsx"
SHEET_NAME = "results"
PROBABILITY_RE = re.compile(r"((?:0|[1-9]\d?|100)(?:\.\d)?)%?\Z")
STOP_REASONS = {"stop", "end_turn", "complete", "completed"}


def parse_probability(raw: object) -> float | None:
    """Read a 0--100 number, tolerating an unambiguous trailing percent sign."""
    text = str(raw or "").strip()
    match = PROBABILITY_RE.fullmatch(text)
    if not match:
        return None
    value = float(match.group(1))
    return value if 0 <= value <= 100 else None


def normalize_answer(value: object) -> str:
    """Match the benchmark's exact option-letter comparison."""
    return str(value or "").strip().upper()


def original_exclusion(answer: str) -> str:
    """Classify the two original-response exclusion markers in the workbook."""
    if not answer:
        return "truncated_original_answer"
    if answer == "失败":
        return "failed_original_answer"
    return ""


def load_rows(path: Path, model_column: str, *, include_gold: bool = True) -> list[dict[str, str]]:
    """Read gold answers only when preparing the post-collection analysis."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if SHEET_NAME not in workbook.sheetnames:
            raise ValueError(f"Missing sheet: {SHEET_NAME}")
        rows = workbook[SHEET_NAME].values
        headers = [str(x or "").strip() for x in next(rows)]
        lower = {h.casefold(): i for i, h in enumerate(headers)}
        required = ["id", "type", "question", model_column]
        if include_gold:
            required.append("gold_answer")
        missing = [name for name in required if name.casefold() not in lower]
        if missing:
            raise ValueError(f"Missing workbook columns: {missing}")
        index = {name: lower[name.casefold()] for name in required}
        result: list[dict[str, str]] = []
        seen: set[str] = set()
        for excel_row, cells in enumerate(rows, 2):
            question_id = str(cells[index["id"]] or "").strip()
            if not question_id or question_id in seen:
                raise ValueError(f"Blank or duplicate id in worksheet row {excel_row}")
            seen.add(question_id)
            common = {
                "id": question_id,
                "question_type": str(cells[index["type"]] or "").strip(),
                "question": str(cells[index["question"]] or ""),
            }
            if include_gold:
                common["gold_answer"] = normalize_answer(cells[index["gold_answer"]])
            if not common["question"].strip() or (include_gold and not common["gold_answer"]):
                raise ValueError(f"Missing question or required gold answer in worksheet row {excel_row}")
            result.append({
                **common,
                "model_answer": str(cells[index[model_column]] or "").strip(),
            })
        return result
    finally:
        workbook.close()


def load_responses(path: Path | list[Path], model_column: str | None = None) -> dict[str, dict[str, object]]:
    """Read JSONL attempts or a released probability workbook by question ID."""
    responses: dict[str, dict[str, object]] = {}
    for source in ([path] if isinstance(path, Path) else path):
        if not source.exists():
            continue
        if source.suffix.lower() == ".xlsx":
            if not model_column:
                raise ValueError("A model column is required for a probability workbook")
            workbook = load_workbook(source, read_only=True, data_only=True)
            try:
                probability_sheet = workbook["probabilities"]
                status_sheet = workbook["response_status"]
                probability_rows = probability_sheet.values
                status_rows = status_sheet.values
                probability_header = list(next(probability_rows))
                status_header = list(next(status_rows))
                if model_column not in probability_header or model_column not in status_header:
                    raise ValueError(f"Missing model column in probability workbook: {model_column}")
                probability_index = probability_header.index(model_column)
                status_index = status_header.index(model_column)
                for values, statuses in zip(probability_rows, status_rows):
                    question_id = str(values[0] or "").strip()
                    if question_id != str(statuses[0] or "").strip():
                        raise ValueError("Probability and status question IDs differ")
                    probability = values[probability_index]
                    status = str(statuses[status_index] or "").strip()
                    if probability is None and not status:
                        continue
                    if probability is not None and not status:
                        status = "ok"
                    responses[question_id] = {
                        "id": question_id, "status": status,
                        "raw_probability": str(probability) if probability is not None else "",
                        "finish_reason": "stop" if status == "ok" else "",
                    }
            finally:
                workbook.close()
            continue
        with source.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    question_id = str(record["id"])
                except (ValueError, KeyError, TypeError) as exc:
                    raise ValueError(f"Invalid JSONL record in {source}:{line_number}") from exc
                responses[question_id] = record
    return responses


def is_valid_response(record: dict[str, object]) -> bool:
    """Reject failed, truncated, blank, and nonnumeric confidence replies."""
    return (
        record.get("status") in {"ok", "invalid_probability_response"}
        and str(record.get("finish_reason") or "").lower() in STOP_REASONS
        and parse_probability(record.get("raw_probability")) is not None
    )


def csv_write(path: Path, records: list[dict[str, object]], headers: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(records)


def analyze(rows: list[dict[str, str]], response_file: Path | list[Path],
            output_dir: Path, model_column: str) -> None:
    """Compute empirical accuracy by probability bin and model-level scores."""
    output_dir.mkdir(parents=True, exist_ok=True)
    detail: list[dict[str, object]] = []
    bins: list[dict[str, object]] = []
    responses = load_responses(response_file, model_column)
    unknown = set(responses) - {row["id"] for row in rows}
    if unknown:
        raise ValueError(f"Unknown question IDs for {model_column}: {sorted(unknown)[:5]}")
    valid: list[dict[str, object]] = []
    exclusions = {"truncated_original_answer": 0, "failed_original_answer": 0,
                  "no_probability_response": 0, "truncated_probability_response": 0,
                  "invalid_probability_response": 0, "failed_probability_response": 0}
    for row in rows:
        answer = row["model_answer"]
        original_status = original_exclusion(answer)
        if original_status:
            exclusions[original_status] += 1
            exclusion = original_status
            probability = None
        else:
            response = responses.get(row["id"])
            if response is None:
                exclusions["no_probability_response"] += 1
                exclusion = "no_probability_response"
                probability = None
            elif not is_valid_response(response):
                status = str(response.get("status") or "")
                exclusion = (status if status in {"truncated_probability_response",
                                                 "invalid_probability_response"}
                             else "failed_probability_response")
                exclusions[exclusion] += 1
                probability = None
            else:
                exclusion = ""
                probability = parse_probability(response["raw_probability"])
        correct = int(bool(answer) and normalize_answer(answer) == row["gold_answer"])
        item = {"model": model_column, "id": row["id"], "model_answer": answer,
                "gold_answer": row["gold_answer"], "correct": correct,
                "probability_percent": probability if probability is not None else "",
                "exclusion_reason": exclusion}
        detail.append(item)
        if probability is not None:
            valid.append(item)
    for bin_index in range(10):
        selected = [x for x in valid if min(int(float(x["probability_percent"]) // 10), 9) == bin_index]
        bins.append({
            "model": model_column, "bin_lower_percent": bin_index * 10,
            "bin_upper_percent": (bin_index + 1) * 10,
            "n": len(selected),
            "mean_probability_percent": round(mean(float(x["probability_percent"]) for x in selected), 3) if selected else "",
            "empirical_accuracy_percent": round(100 * mean(int(x["correct"]) for x in selected), 3) if selected else "",
        })
    ece_sum = sum(
        int(b["n"]) * abs(float(b["mean_probability_percent"]) - float(b["empirical_accuracy_percent"]))
        for b in bins if b["n"]
    )
    summary = [{"model": model_column, "total_questions": len(rows),
                "truncated_original_answer": exclusions["truncated_original_answer"],
                "failed_original_answer": exclusions["failed_original_answer"],
                "no_probability_response": exclusions["no_probability_response"],
                "truncated_probability_response": exclusions["truncated_probability_response"],
                "invalid_probability_response": exclusions["invalid_probability_response"],
                "failed_probability_response": exclusions["failed_probability_response"],
                "analyzed_questions": len(valid),
                "accuracy_percent": round(100 * mean(int(x["correct"]) for x in valid), 3) if valid else "",
                "mean_probability_percent": round(mean(float(x["probability_percent"]) for x in valid), 3) if valid else "",
                "ece_percent": round(ece_sum / len(valid), 4) if valid else ""}]
    csv_write(output_dir / "calibration_probability_questions.csv", detail, list(detail[0]))
    csv_write(output_dir / "calibration_probability_summary.csv", summary, list(summary[0]))
    csv_write(output_dir / "calibration_probability_bins.csv", bins, list(bins[0]))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


RETRYABLE_HTTP = {408, 409, 429, 500, 502, 503, 504}
DEFAULT_TEMPERATURE = 0
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MAX_RETRIES = 3

# Exact Chinese user message; no system message or few-shot examples are sent.
PROBABILITY_PROMPT = """以下是你此前对一道题目给出的答案。请估计该答案完全正确的概率，不要重新作答。

题目类型：{question_type}
题目：{question}
你给出的答案：{answer}

“完全正确”指整个答案被判定为正确。对于多选题，只有所有正确选项均被选中，且没有多选错误选项，才算完全正确；漏选或多选均算错误。

这里的概率是指“整个答案完全正确”的可能性：50%表示你认为该答案完全正确与不完全正确的可能性相同，并不表示答案有一半内容正确。

请给出你认为该答案完全正确的概率，范围为0%至100%。只输出一个0至100之间的数字，可保留一位小数；不要输出百分号、解释或其他文字。"""


def build_prompt(row: dict[str, str]) -> str:
    """Interpolate only the question, type, and original model answer."""
    return PROBABILITY_PROMPT.format(
        question_type=row["question_type"], question=row["question"], answer=row["model_answer"]
    )


def request_body(row: dict[str, str], args: argparse.Namespace) -> dict[str, object]:
    """Send only the original question, type, and model answer."""
    body: dict[str, object] = {
        "model": args.api_model,
        "messages": [{"role": "user", "content": build_prompt(row)}],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "stream": False,
    }
    if args.top_p is not None:
        body["top_p"] = args.top_p
    if args.reasoning_json:
        body["reasoning"] = json.loads(args.reasoning_json)
    return body


def collect_one(row: dict[str, str], args: argparse.Namespace, api_key: str) -> dict[str, object]:
    """Retry transport errors and invalid probability replies."""
    encoded = json.dumps(request_body(row, args), ensure_ascii=False).encode("utf-8")
    result: dict[str, object] = {
        "id": row["id"], "model": args.model_column, "api_model": args.api_model,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    for attempt in range(1, args.max_retries + 1):
        request = Request(args.api_url, data=encoded, headers={
            "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"
        }, method="POST")
        retryable = True
        try:
            with urlopen(request, timeout=args.timeout) as response:
                data = json.load(response)
            choice = data["choices"][0]
            content = (choice.get("message") or {}).get("content") or ""
            if isinstance(content, list):
                content = "".join(str(p.get("text", "")) for p in content if isinstance(p, dict))
            raw = str(content).strip()
            finish = str(choice.get("finish_reason") or "").lower()
            probability = parse_probability(raw)
            status = "ok" if finish in STOP_REASONS and probability is not None else (
                "truncated_probability_response" if finish in {"length", "max_tokens"}
                else "invalid_probability_response"
            )
            result.update({"status": status, "attempts": attempt,
                           "raw_probability": raw, "probability_percent": probability,
                           "finish_reason": finish, "returned_model": data.get("model", ""),
                           "usage": data.get("usage") or {}})
            if status == "ok":
                return result
        except HTTPError as exc:
            result.update({"status": "http_error", "attempts": attempt,
                           "error_type": f"HTTP_{exc.code}", "raw_probability": "",
                           "finish_reason": ""})
            retryable = exc.code in RETRYABLE_HTTP
        except (URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            result.update({"status": "request_error", "attempts": attempt,
                           "error_type": type(exc).__name__, "raw_probability": "",
                           "finish_reason": ""})
        if not retryable:
            break
        if attempt < args.max_retries:
            time.sleep(min(2 ** (attempt - 1), 20))
    return result


def collect_main(argv: list[str]) -> None:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=script_dir / WORKBOOK_NAME)
    parser.add_argument("--model-column", required=True, help="One model answer column in the results sheet")
    parser.add_argument("--api-model", required=True, help="Model ID on the selected API")
    parser.add_argument("--api-url", required=True, help="HTTPS chat/completions endpoint")
    parser.add_argument("--api-key-env", required=True, help="Environment variable holding the API key")
    parser.add_argument("--output", type=Path, required=True, help="JSONL output file")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--top-p", type=float, default=None, help="Omit for provider default")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--retest-from", type=Path,
                        help="First-pass JSONL; retest only its unresolved truncated replies")
    parser.add_argument("--retest-invalid", action="store_true",
                        help="Also retest unresolved invalid replies (if used in the study run)")
    parser.add_argument("--reasoning-json", default="", help="Optional provider reasoning settings as JSON")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--limit", type=int, default=0, help="Maximum pending questions; 0 means all")
    parser.add_argument("--execute", action="store_true", help="Send real API requests")
    args = parser.parse_args(argv)
    if args.retest_from and args.max_tokens == DEFAULT_MAX_TOKENS:
        args.max_tokens = 8192
    if args.retest_from and args.output.resolve() == args.retest_from.resolve():
        parser.error("Retest output must differ from the first-pass JSONL")
    if not args.api_url.startswith("https://"):
        parser.error("--api-url must be HTTPS")
    if args.max_tokens < 1 or args.timeout < 1 or args.max_retries < 1 or args.limit < 0:
        parser.error("Invalid numeric setting")
    if args.top_p is not None and not 0 < args.top_p <= 1:
        parser.error("--top-p must be in (0, 1]")
    if args.reasoning_json:
        try:
            reasoning = json.loads(args.reasoning_json)
        except ValueError as exc:
            parser.error(f"Invalid --reasoning-json: {exc}")
        if not isinstance(reasoning, dict):
            parser.error("--reasoning-json must be a JSON object")
    rows = load_rows(args.input, args.model_column, include_gold=False)
    eligible = [r for r in rows if not original_exclusion(r["model_answer"])]
    if args.retest_from:
        if not args.retest_from.is_file():
            parser.error(f"First-pass JSONL not found: {args.retest_from}")
        first_pass = load_responses(args.retest_from)
        statuses = {"truncated_probability_response"}
        if args.retest_invalid:
            statuses.add("invalid_probability_response")
        eligible = [r for r in eligible if first_pass.get(r["id"], {}).get("status") in statuses]
    if not args.execute:
        print(json.dumps({"api_requests_sent": 0, "model_column": args.model_column,
                          "eligible_questions": len(eligible),
                          "truncated_original_answers": sum(not r["model_answer"] for r in rows),
                          "failed_original_answers": sum(r["model_answer"] == "失败" for r in rows),
                          "api_url": args.api_url,
                          "request_example": request_body(eligible[0], args) if eligible else None},
                         ensure_ascii=False, indent=2))
        return
    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        raise SystemExit(f"Missing environment variable: {args.api_key_env}")
    plan = {"input_workbook_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
            "prompt_sha256": hashlib.sha256(PROBABILITY_PROMPT.encode("utf-8")).hexdigest(),
            "model_column": args.model_column, "api_model": args.api_model,
            "api_url": args.api_url, "api_key_env": args.api_key_env,
            "temperature": args.temperature, "top_p": args.top_p,
            "max_tokens": args.max_tokens, "reasoning_json": args.reasoning_json,
            "stream": False, "system_message": None, "few_shot_count": 0,
            "timeout_seconds": args.timeout, "max_retries": args.max_retries,
            "original_answer_exclusions": ["blank_truncated", "失败"],
            "retest_source_sha256": (hashlib.sha256(args.retest_from.read_bytes()).hexdigest()
                                     if args.retest_from else None),
            "retest_invalid": args.retest_invalid}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output.with_suffix(args.output.suffix + ".manifest.json")
    if manifest_path.exists():
        if json.loads(manifest_path.read_text(encoding="utf-8")) != plan:
            raise SystemExit("Existing output has different input, prompt, or request settings")
    elif args.output.exists() and args.output.stat().st_size:
        raise SystemExit("Existing output lacks a manifest; choose a new output path")
    else:
        manifest_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    completed = {qid for qid, record in load_responses(args.output).items()
                 if is_valid_response(record)}
    pending = [r for r in eligible if r["id"] not in completed]
    if args.limit:
        pending = pending[:args.limit]
    print(f"{len(pending)} pending questions for {args.model_column}", file=sys.stderr)
    with args.output.open("a", encoding="utf-8") as handle:
        for number, row in enumerate(pending, 1):
            handle.write(json.dumps(collect_one(row, args, api_key), ensure_ascii=False) + "\n")
            handle.flush()
            if number % 100 == 0 or number == len(pending):
                print(f"Saved {number}/{len(pending)}", file=sys.stderr)


def analyze_main(argv: list[str]) -> None:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=script_dir / WORKBOOK_NAME)
    parser.add_argument("--model-column", required=True, help="Name of one model answer column")
    parser.add_argument("--responses", type=Path, nargs="+",
                        help="Released probability XLSX, or first-pass JSONL followed by retest JSONLs")
    parser.add_argument("--output-dir", type=Path, default=script_dir / "calibration_probability_results")
    args = parser.parse_args(argv)
    rows = load_rows(args.input, args.model_column)
    if args.responses:
        analyze(rows, args.responses, args.output_dir, args.model_column)
    else:
        eligible = [r for r in rows if not original_exclusion(r["model_answer"])]
        print(json.dumps({"model_column": args.model_column, "eligible_questions": len(eligible),
                          "truncated_original_answer": sum(not r["model_answer"] for r in rows),
                          "failed_original_answer": sum(r["model_answer"] == "失败" for r in rows)},
                         ensure_ascii=False, indent=2))


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {"collect", "analyze"}:
        raise SystemExit("Usage: python calibration.py {collect|analyze} [options]")
    command, arguments = sys.argv[1], sys.argv[2:]
    if command == "collect":
        collect_main(arguments)
    else:
        analyze_main(arguments)


if __name__ == "__main__":
    main()
