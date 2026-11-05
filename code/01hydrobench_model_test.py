"""Public Hydro-SE Bench API evaluation script (Chinese or English prompt).

This is a reusable presentation script. Select the model, endpoint and API
settings on the command line; do not put credentials in source code. The prompt
is sent as one user message. The model's original reply and the option letters
extracted by the rules below are saved.

Examples (PowerShell; replace the model and endpoint with the tested version):
  python hydrobench_model_test.py --list-models
  python hydrobench_model_test.py --dataset hydrobench.json --language zh --model MODEL_ID --api-url https://example.com/v1/chat/completions --api-key-env PROVIDER_API_KEY --output results_zh.jsonl
  python hydrobench_model_test.py --dataset hydrobench.json --language zh --model-name "Qwen3.6-Plus" --api-url https://example.com/v1/chat/completions --api-key-env PROVIDER_API_KEY --output results_zh.jsonl
  python hydrobench_model_test.py --dataset hydrobench_en.json --language en --model MODEL_ID --api-url https://example.com/v1/chat/completions --api-key-env PROVIDER_API_KEY --output results_en.jsonl --execute

Without --execute, the script only previews one request and sends no API call.
Requires Python 3.10+ and uses the standard library only.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CHINESE_PROMPT = """你是水利水电领域的专家，请以专业的角度回答下面的【{question_type}】，并给出全部正确的答案选项。
请严格按以下格式回答：
1. 先给出简短解题过程，说明判断依据。
2. 最后一行必须严格输出：最终答案：<选项字母>
要求：单选题只输出一个字母，例如“最终答案：A”；多选题输出所有正确字母，并按字母顺序排列，例如“最终答案：ACD”。最后一行不要包含解释或其他文字。

题目：
{question}"""

ENGLISH_PROMPT = """You are an expert in hydrology, water resources, hydraulic engineering, geotechnical engineering, fluid mechanics, and related engineering fields.
Please answer the following {question_type} from a professional perspective and provide all the correct answer options.
Please follow this format strictly:.
1. Provide a necessary and concise reasoning process first.
2. The last line must strictly follow this format: Final answer: <option letters>
Requirements: For single-choice questions, output only one letter, for example: Final answer: A. For multiple-choice questions, output all correct letters in alphabetical order, for example: Final answer: ACD. Do not include explanations or other text on the final line.

Question:
{question}"""

QUESTION_TYPES = {
    "zh": {"single choice": "单项选择题", "multiple choice": "多项选择题"},
    "en": {"single choice": "single-choice question", "multiple choice": "multiple-choice question"},
}
OPTION_RE = re.compile(r"[A-H]")
RETRYABLE_HTTP = {408, 409, 429, 500, 502, 503, 504}

# Exact model identifiers used in the Hydro-SE Bench evaluation. Display names
# match the manuscript; API access channels and access dates match the
# ``model_status`` worksheet in ``hydrobench_final_model_answer_table.xlsx``.
# ``exact_identifier`` is the value supplied in the API request's ``model``
# field. Keeping this registry in the released script makes the evaluated model
# versions explicit and machine-readable.
EVALUATED_MODELS: tuple[dict[str, str], ...] = (
    {"display_name": "Qwen3.6-Plus", "exact_identifier": "qwen3.6-plus-2026-04-02", "api_access_channel": "Official API", "access_date": "2026-07-21"},
    {"display_name": "GPT-5.6-Sol", "exact_identifier": "gpt-5.6-sol", "api_access_channel": "OpenRouter", "access_date": "2026-07-21"},
    {"display_name": "DeepSeek-V4-Pro", "exact_identifier": "deepseek-v4-pro", "api_access_channel": "Official API", "access_date": "2026-07-18"},
    {"display_name": "GLM-5.1", "exact_identifier": "glm-5.1", "api_access_channel": "Official API", "access_date": "2026-07-17"},
    {"display_name": "Qwen3.5-397B-A17B", "exact_identifier": "qwen3.5-397b-a17b", "api_access_channel": "Official API", "access_date": "2026-07-21"},
    {"display_name": "Qwen3.5-122B-A10B", "exact_identifier": "qwen3.5-122b-a10b", "api_access_channel": "Official API", "access_date": "2026-07-21"},
    {"display_name": "Qwen3.7-Plus", "exact_identifier": "qwen3.7-plus-2026-05-26", "api_access_channel": "Official API", "access_date": "2026-07-21"},
    {"display_name": "DeepSeek-V3.2-Exp", "exact_identifier": "deepseek-v3.2-exp", "api_access_channel": "Official API", "access_date": "2025-09-29"},
    {"display_name": "DeepSeek-R1", "exact_identifier": "deepseek-reasoner", "api_access_channel": "Official API", "access_date": "2025-10-16"},
    {"display_name": "DeepSeek-V4-Flash", "exact_identifier": "deepseek-v4-flash", "api_access_channel": "Official API", "access_date": "2026-07-21"},
    {"display_name": "Qwen3.5-35B-A3B", "exact_identifier": "qwen3.5-35b-a3b", "api_access_channel": "Official API", "access_date": "2026-07-21"},
    {"display_name": "Kimi K2-0905", "exact_identifier": "kimi-k2-0905-preview", "api_access_channel": "Official API", "access_date": "2025-09-29"},
    {"display_name": "GLM-4.5", "exact_identifier": "glm-4.5", "api_access_channel": "Official API", "access_date": "2025-09-29"},
    {"display_name": "Qwen3-235B-A22B-Instruct", "exact_identifier": "qwen3-235b-a22b-instruct-2507", "api_access_channel": "Official API", "access_date": "2026-07-21"},
    {"display_name": "GPT-5", "exact_identifier": "openai/gpt-5", "api_access_channel": "OpenRouter", "access_date": "2025-10-16"},
    {"display_name": "Grok 4", "exact_identifier": "x-ai/grok-4", "api_access_channel": "OpenRouter", "access_date": "2025-10-17"},
    {"display_name": "GPT-5.4", "exact_identifier": "gpt-5.4", "api_access_channel": "OpenRouter", "access_date": "2026-07-21"},
    {"display_name": "Qwen-Plus", "exact_identifier": "qwen-plus", "api_access_channel": "Official API", "access_date": "2025-09-29"},
    {"display_name": "Gemini 2.5 Pro", "exact_identifier": "google/gemini-2.5-pro", "api_access_channel": "OpenRouter", "access_date": "2025-10-18"},
    {"display_name": "Llama 4 Maverick", "exact_identifier": "meta-llama/llama-4-maverick", "api_access_channel": "OpenRouter", "access_date": "2025-10-20"},
    {"display_name": "Qwen3-Next-80B-A3B-Instruct", "exact_identifier": "qwen3-next-80b-a3b-instruct", "api_access_channel": "Official API", "access_date": "2026-07-21"},
    {"display_name": "Claude Sonnet 4.5", "exact_identifier": "anthropic/claude-sonnet-4.5", "api_access_channel": "OpenRouter", "access_date": "2025-10-18"},
    {"display_name": "Qwen3-32B", "exact_identifier": "qwen3-32b", "api_access_channel": "Official API", "access_date": "2026-07-21"},
    {"display_name": "Qwen3-30B-A3B-Instruct", "exact_identifier": "qwen3-30b-a3b-instruct-2507", "api_access_channel": "Official API", "access_date": "2026-07-21"},
    {"display_name": "GLM-4-32B", "exact_identifier": "z-ai/glm-4-32b", "api_access_channel": "Official API", "access_date": "2025-10-26"},
    {"display_name": "Qwen3-8B", "exact_identifier": "qwen3-8b", "api_access_channel": "Official API", "access_date": "2026-07-20"},
    {"display_name": "Qwen2.5-32B-Instruct", "exact_identifier": "qwen2.5-32b-instruct", "api_access_channel": "Official API", "access_date": "2025-10-20"},
    {"display_name": "Qwen2.5-72B-Instruct", "exact_identifier": "qwen2.5-72b-instruct", "api_access_channel": "Official API", "access_date": "2025-10-20"},
    {"display_name": "Llama 4 Scout", "exact_identifier": "meta-llama/llama-4-scout", "api_access_channel": "OpenRouter", "access_date": "2026-07-21"},
    {"display_name": "Llama 3.3 70B Instruct", "exact_identifier": "meta-llama/llama-3.3-70b-instruct", "api_access_channel": "OpenRouter", "access_date": "2026-07-21"},
    {"display_name": "Qwen2.5-7B-Instruct", "exact_identifier": "qwen2.5-7b-instruct", "api_access_channel": "Official API", "access_date": "2025-10-18"},
    {"display_name": "Llama 3.1 70B Instruct", "exact_identifier": "meta-llama/llama-3.1-70b-instruct", "api_access_channel": "OpenRouter", "access_date": "2026-07-21"},
    {"display_name": "Llama 3 70B Instruct", "exact_identifier": "meta-llama/llama-3-70b-instruct", "api_access_channel": "OpenRouter", "access_date": "2025-10-20"},
    {"display_name": "Llama 3 8B Instruct", "exact_identifier": "meta-llama/llama-3-8b-instruct", "api_access_channel": "OpenRouter", "access_date": "2025-10-20"},
    {"display_name": "Llama 3.1 8B Instruct", "exact_identifier": "meta-llama/llama-3.1-8b-instruct", "api_access_channel": "OpenRouter", "access_date": "2026-07-21"},
    {"display_name": "Llama 3.2 3B Instruct", "exact_identifier": "meta-llama/llama-3.2-3b-instruct", "api_access_channel": "OpenRouter", "access_date": "2026-07-21"},
    {"display_name": "Llama 3.2 1B Instruct", "exact_identifier": "meta-llama/llama-3.2-1b-instruct", "api_access_channel": "OpenRouter", "access_date": "2026-07-21"},
)
MODEL_BY_NAME = {item["display_name"]: item for item in EVALUATED_MODELS}


def extract_answer_details(text: object) -> dict[str, Any]:
    """Rule-based extractor"""
    result = {
        "extracted_answer": "",
        "extraction_method": "",
        "answer_format_ok": False,
        "answer_line": "",
    }
    if not text:
        return result

    raw = str(text)
    normalized = raw.upper().replace("：", ":").replace("，", ",").replace("；", ";")
    patterns = [
        ("final_answer_line", r"^\s*FINAL\s+ANSWER\s*:\s*([A-H][A-H\s,;]*)\s*$", re.MULTILINE),
        ("final_answer_inline", r"FINAL\s+ANSWER\s*:\s*([A-H][A-H\s,;]*)", 0),
        (
            "answer_label",
            r"(?:CORRECT\s+OPTION|CORRECT\s+ANSWER|ANSWER|FINAL\s+ANSWER|最终答案|答案|正确答案)\s*[:]\s*([A-H][A-H\s,;]*)",
            0,
        ),
        ("json_answer", r'"(?:ANSWER|FINAL_ANSWER|FINAL ANSWER)"\s*:\s*"([A-H][A-H\s,;]*)"', 0),
    ]
    for method, pattern, flags in patterns:
        match = re.search(pattern, normalized, flags)
        if not match:
            continue
        letters = OPTION_RE.findall(match.group(1))
        if letters:
            result["extracted_answer"] = "".join(sorted(set(letters)))
            result["extraction_method"] = method
            result["answer_format_ok"] = method == "final_answer_line"
            result["answer_line"] = match.group(0).strip()
            return result

    tail = "\n".join(normalized.splitlines()[-10:])
    letters = re.findall(r"\b([A-H])\b", tail)
    if letters:
        result["extracted_answer"] = "".join(sorted(set(letters)))
        result["extraction_method"] = "tail_fallback"
        result["answer_line"] = tail.strip()
    return result


def build_prompt(example: dict[str, Any], language: str) -> str:
    question_type = QUESTION_TYPES[language][example["type"]]
    template = CHINESE_PROMPT if language == "zh" else ENGLISH_PROMPT
    return template.format(question_type=question_type, question=example["input"])


def build_request_body(example: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": args.model,
        "messages": [{"role": "user", "content": build_prompt(example, args.language)}],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "stream": args.thinking_parameter == "enable_thinking" and args.thinking == "enabled",
    }
    if args.thinking_parameter == "thinking" and args.thinking != "default":
        body["thinking"] = {"type": args.thinking}
    elif args.thinking_parameter == "enable_thinking" and args.thinking != "default":
        body["enable_thinking"] = args.thinking == "enabled"
    elif args.thinking_parameter == "reasoning" and args.thinking != "default":
        body["reasoning"] = {"enabled": args.thinking == "enabled"}
        if args.reasoning_effort:
            body["reasoning"]["effort"] = args.reasoning_effort
    if args.reasoning_effort and args.thinking_parameter == "thinking":
        body["reasoning_effort"] = args.reasoning_effort
    # Non-streaming chat/completions responses normally include usage. For
    # streaming responses, explicitly ask for the final usage event.
    if body["stream"]:
        body["stream_options"] = {"include_usage": True}
    return body


def load_examples(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    examples = data.get("examples")
    if not isinstance(examples, list) or not examples:
        raise ValueError("Dataset must contain a nonempty 'examples' list")
    for index, example in enumerate(examples, 1):
        if example.get("type") not in QUESTION_TYPES["zh"]:
            raise ValueError(f"Unsupported question type at row {index}")
        if not isinstance(example.get("input"), str) or not example["input"].strip():
            raise ValueError(f"Missing question text at row {index}")
    return examples


def read_api_response(response: Any, streamed: bool) -> tuple[str, str, dict[str, Any], str]:
    if not streamed:
        data = json.load(response)
        choice = data["choices"][0]
        message = choice.get("message") or {}
        content = message.get("content") or ""
        if isinstance(content, list):
            content = "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
        reasoning = message.get("reasoning_content") or message.get("reasoning") or ""
        return (str(content), str(reasoning), data.get("usage") or {},
                str(choice.get("finish_reason") or ""))

    parts: list[str] = []
    reasoning_parts: list[str] = []
    usage: dict[str, Any] = {}
    finish_reason = ""
    for raw_line in response:
        line = raw_line.decode("utf-8").strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        if not payload:
            continue
        event = json.loads(payload)
        usage = event.get("usage") or usage
        for choice in event.get("choices") or []:
            delta = choice.get("delta") or {}
            parts.append(str(delta.get("content") or ""))
            reasoning_parts.append(str(delta.get("reasoning_content") or ""))
            finish_reason = str(choice.get("finish_reason") or finish_reason)
    return "".join(parts), "".join(reasoning_parts), usage, finish_reason


def token_counts(usage: dict[str, Any]) -> dict[str, int | None]:
    """Keep API-reported counts; use None when a provider omits a value."""
    def count(*names: str) -> int | None:
        for name in names:
            value = usage.get(name)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                return value
        return None

    return {
        "prompt_tokens": count("prompt_tokens", "input_tokens"),
        "completion_tokens": count("completion_tokens", "output_tokens"),
        "total_tokens": count("total_tokens"),
    }


def evaluate_one(index: int, example: dict[str, Any], args: argparse.Namespace, api_key: str) -> dict[str, Any]:
    body = build_request_body(example, args)
    custom_id = f"{index:04d}_{example.get('ID', index)}"
    record: dict[str, Any] = {
        "custom_id": custom_id,
        "id": example.get("ID"),
        "type": example["type"],
        "question": example["input"],
        "language": args.language,
        "model_display_name": args.model_name or "",
        "api_access_channel": MODEL_BY_NAME.get(args.model_name or "", {}).get("api_access_channel", ""),
        "model": args.model,
        "request_settings": {key: value for key, value in body.items() if key != "messages"},
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
    last_error = ""
    for attempt in range(1, args.max_retries + 1):
        request = Request(
            args.api_url,
            data=encoded,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=args.timeout) as response:
                answer, reasoning, usage, finish_reason = read_api_response(response, body["stream"])
            parsed = extract_answer_details(answer)
            record.update({
                "status": "ok" if parsed["extracted_answer"] else "empty_or_unparsed",
                "attempts": attempt, "model_answer": answer,
                "extracted_answer": parsed["extracted_answer"],
                "reasoning_content": reasoning, "usage": usage,
                "finish_reason": finish_reason,
                **token_counts(usage),
            })
            return record
        except HTTPError as exc:
            last_error = f"HTTP {exc.code}"
            if exc.code not in RETRYABLE_HTTP:
                break
        except (URLError, TimeoutError, OSError, ValueError, KeyError, IndexError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < args.max_retries:
            time.sleep(min(2 ** (attempt - 1), 30))
    record.update({
        "status": "error", "attempts": attempt, "error": last_error,
        "model_answer": "", "extracted_answer": "",
        "reasoning_content": "", "usage": {}, "finish_reason": "",
        **token_counts({}),
    })
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list-models", action="store_true", help="Print the 37 evaluated models and exit")
    parser.add_argument("--dataset", type=Path, help="HydroBench JSON with an examples list")
    parser.add_argument("--language", choices=["zh", "en"])
    parser.add_argument("--model", help="Exact API model identifier; overrides no registry value")
    parser.add_argument(
        "--model-name", choices=tuple(MODEL_BY_NAME),
        help="Manuscript model name; resolves to the registered exact identifier",
    )
    parser.add_argument("--api-url", help="Full chat/completions endpoint URL")
    parser.add_argument("--api-key-env", help="Name of an environment variable holding the API key")
    parser.add_argument("--output", type=Path, help="Result JSONL path")
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--thinking-parameter", choices=["none", "thinking", "enable_thinking", "reasoning"], default="none")
    parser.add_argument("--thinking", choices=["default", "enabled", "disabled"], default="default")
    parser.add_argument("--reasoning-effort", default="", help="Optional provider-specific effort value")
    parser.add_argument("--limit", type=int, default=0, help="Run or preview the first N pending questions; 0 means all")
    parser.add_argument("--execute", action="store_true", help="Actually call the API; omitted means preview only")
    args = parser.parse_args()
    if args.list_models:
        return args
    required = {
        "--dataset": args.dataset,
        "--language": args.language,
        "--api-url": args.api_url,
        "--api-key-env": args.api_key_env,
        "--output": args.output,
    }
    missing = [flag for flag, value in required.items() if value is None]
    if missing:
        parser.error(f"Missing required arguments: {', '.join(missing)}")
    if args.model_name:
        registered_identifier = MODEL_BY_NAME[args.model_name]["exact_identifier"]
        if args.model and args.model != registered_identifier:
            parser.error(
                f"--model does not match the registered identifier for {args.model_name}: "
                f"{registered_identifier}"
            )
        args.model = registered_identifier
    if not args.model:
        parser.error("Specify either --model-name or --model")
    if args.concurrency < 1 or args.max_retries < 1 or args.max_tokens < 1 or args.timeout <= 0 or args.limit < 0:
        parser.error("Invalid numeric setting")
    if args.reasoning_effort and args.thinking_parameter not in {"thinking", "reasoning"}:
        parser.error("--reasoning-effort requires --thinking-parameter thinking or reasoning")
    if args.thinking != "default" and args.thinking_parameter == "none":
        parser.error("--thinking requires a --thinking-parameter")
    if args.thinking_parameter == "reasoning" and args.reasoning_effort and args.thinking == "default":
        parser.error("--reasoning-effort with reasoning requires --thinking enabled or disabled")
    return args


def main() -> None:
    args = parse_args()
    if args.list_models:
        print(json.dumps(EVALUATED_MODELS, ensure_ascii=False, indent=2))
        return
    examples = load_examples(args.dataset)
    selected = list(enumerate(examples, 1))
    if not args.execute:
        print(json.dumps({
            "api_requests_sent": 0, "api_url": args.api_url,
            "registered_model": MODEL_BY_NAME.get(args.model_name or ""),
            "request_body_example": build_request_body(examples[0], args),
            "total_questions": len(examples),
        }, ensure_ascii=False, indent=2))
        return

    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        raise SystemExit(f"API key environment variable is not set: {args.api_key_env}")

    prompt = CHINESE_PROMPT if args.language == "zh" else ENGLISH_PROMPT
    plan = {
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "language": args.language, "model": args.model, "api_url": args.api_url,
        "model_display_name": args.model_name or "",
        "registered_model": MODEL_BY_NAME.get(args.model_name or ""),
        "api_key_environment_variable": args.api_key_env,
        "temperature": args.temperature, "max_tokens": args.max_tokens,
        "concurrency": args.concurrency, "timeout_seconds": args.timeout,
        "max_retries": args.max_retries,
        "thinking_parameter": args.thinking_parameter, "thinking": args.thinking,
        "reasoning_effort": args.reasoning_effort,
    }
    manifest_path = args.output.with_suffix(args.output.suffix + ".manifest.json")
    if manifest_path.exists():
        if json.loads(manifest_path.read_text(encoding="utf-8")) != plan:
            raise SystemExit("Existing output has a different dataset, prompt or request configuration")
    elif args.output.exists() and args.output.stat().st_size:
        raise SystemExit("Existing output lacks its manifest; choose a new output path")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    completed: set[str] = set()
    if args.output.exists():
        for line in args.output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                previous = json.loads(line)
                if previous.get("status") == "ok":
                    completed.add(str(previous.get("custom_id")))
    pending = [(i, ex) for i, ex in selected if f"{i:04d}_{ex.get('ID', i)}" not in completed]
    if args.limit:
        pending = pending[:args.limit]
    print(f"Selected {len(pending)} questions; language={args.language}; model={args.model}", file=sys.stderr)
    with args.output.open("a", encoding="utf-8") as handle:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = [pool.submit(evaluate_one, i, ex, args, api_key) for i, ex in pending]
            for number, future in enumerate(as_completed(futures), 1):
                result = future.result()
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")
                handle.flush()
                if number % 50 == 0 or number == len(pending):
                    print(f"Saved {number}/{len(pending)}", file=sys.stderr)


if __name__ == "__main__":
    main()
