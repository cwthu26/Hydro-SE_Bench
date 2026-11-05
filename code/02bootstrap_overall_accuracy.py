#!/usr/bin/env python3
"""Calculate overall model accuracy and stratified bootstrap intervals.

The script reads ``hydrobench_final_model_answer_table.xlsx`` from the same
directory as this file by default. Questions are stratified by Hydro-SE Bench
subfield, task level (A/B/C), and question format (single/multiple choice).
Each bootstrap replicate samples, with
replacement, the original number of questions from every stratum.

Dependencies: numpy, openpyxl
"""

from __future__ import annotations

import argparse
import csv
from collections import OrderedDict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Iterable

import numpy as np
from openpyxl import load_workbook


DEFAULT_INPUT_NAME = "hydrobench_final_model_answer_table.xlsx"
DEFAULT_OUTPUT_NAME = "Overall_accuracy_bootstrap.csv"
DEFAULT_SHEET = "results"
DEFAULT_BOOTSTRAPS = 10_000
DEFAULT_SEED = 42
DEFAULT_CONFIDENCE_LEVEL = 0.95
DEFAULT_MODEL_CHUNK_SIZE = 8

METADATA_COLUMNS = {
    "row_index",
    "custom_id",
    "id",
    "category_sheet",
    "level",
    "type",
    "question",
    "gold_answer",
}


def canonical_header(value: object) -> object:
    """Map supported result-table header variants to canonical names."""
    if not isinstance(value, str):
        return value
    text = value.strip()
    aliases = {
        "row_index": "row_index",
        "custom_id": "custom_id",
        "id": "id",
        "category_sheet": "category_sheet",
        "level": "level",
        "type": "type",
        "question": "question",
        "answer": "gold_answer",
        "gold_answer": "gold_answer",
    }
    return aliases.get(text.lower(), text)


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description=(
            "Calculate model accuracy and subfield-by-level-by-format stratified "
            "bootstrap confidence intervals for manuscript Table 7."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=script_dir / DEFAULT_INPUT_NAME,
        help="Input workbook (default: workbook in the script directory).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=script_dir / DEFAULT_OUTPUT_NAME,
        help="Output CSV file (default: CSV in the script directory).",
    )
    parser.add_argument("--sheet", default=DEFAULT_SHEET, help="Worksheet name.")
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=DEFAULT_BOOTSTRAPS,
        help="Number of bootstrap replicates (default: 10000).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Random seed (default: 42).",
    )
    parser.add_argument(
        "--confidence-level",
        type=float,
        default=DEFAULT_CONFIDENCE_LEVEL,
        help="Two-sided confidence level (default: 0.95).",
    )
    parser.add_argument(
        "--model-chunk-size",
        type=int,
        default=DEFAULT_MODEL_CHUNK_SIZE,
        help="Model columns processed at once to limit memory use (default: 8).",
    )
    parser.add_argument(
        "--expected-questions",
        type=int,
        default=4000,
        help="Required number of questions; use 0 to disable the check.",
    )
    return parser.parse_args()


def normalize_answer(value: object) -> str:
    """Normalize an answer for exact option-set comparison."""
    if value is None:
        return ""
    return str(value).strip().upper()


def half_up(value: float, digits: int) -> Decimal:
    """Round a numeric value by the conventional round-half-up rule."""
    quantum = Decimal("1").scaleb(-digits)
    return Decimal(f"{value:.12f}").quantize(quantum, rounding=ROUND_HALF_UP)


def load_correctness_matrix(
    workbook_path: Path,
    sheet_name: str,
    expected_questions: int,
) -> tuple[list[str], np.ndarray, OrderedDict[tuple[str, str, str], np.ndarray]]:
    """Read the result table and return models, correctness, and strata."""
    if not workbook_path.is_file():
        raise FileNotFoundError(f"Input workbook not found: {workbook_path}")

    workbook = load_workbook(workbook_path, data_only=True, read_only=False)
    if sheet_name not in workbook.sheetnames:
        raise ValueError(
            f"Worksheet {sheet_name!r} not found. Available: {workbook.sheetnames}"
        )
    sheet = workbook[sheet_name]
    headers = [canonical_header(cell.value) for cell in sheet[1]]
    if len(headers) != len(set(headers)):
        raise ValueError("The worksheet contains duplicate column headers.")

    required = {"id", "category_sheet", "level", "type", "gold_answer"}
    missing = required.difference(headers)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    column = {name: index for index, name in enumerate(headers)}
    models = [name for name in headers if name not in METADATA_COLUMNS]
    if not models:
        raise ValueError("No model result columns were found.")

    rows = list(sheet.iter_rows(min_row=2, values_only=True))
    if expected_questions and len(rows) != expected_questions:
        raise ValueError(
            f"Expected {expected_questions} questions, found {len(rows)}."
        )

    ids = [str(row[column["id"]]).strip() for row in rows]
    if any(not item for item in ids):
        raise ValueError("The id column contains blank values.")

    gold = [normalize_answer(row[column["gold_answer"]]) for row in rows]
    if any(not answer for answer in gold):
        raise ValueError("The gold_answer column contains blank values.")

    correctness = np.empty((len(rows), len(models)), dtype=np.int8)
    for model_index, model in enumerate(models):
        model_column = column[model]
        correctness[:, model_index] = [
            int(normalize_answer(row[model_column]) == gold[row_index])
            for row_index, row in enumerate(rows)
        ]

    grouped: OrderedDict[tuple[str, str, str], list[int]] = OrderedDict()
    for row_index, row in enumerate(rows):
        domain = str(row[column["category_sheet"]]).strip()
        level = str(row[column["level"]]).strip()
        question_type = str(row[column["type"]]).strip()
        if not domain or level not in {"A", "B", "C"} or not question_type:
            raise ValueError(
                f"Invalid stratum label in worksheet row {row_index + 2}."
            )
        grouped.setdefault((domain, level, question_type), []).append(row_index)

    strata = OrderedDict(
        (key, np.asarray(indices, dtype=np.int32))
        for key, indices in grouped.items()
    )
    return models, correctness, strata


def stratified_bootstrap_accuracy(
    correctness: np.ndarray,
    strata: Iterable[np.ndarray],
    n_bootstrap: int,
    seed: int,
    model_chunk_size: int,
) -> np.ndarray:
    """Return bootstrap model accuracies in percentage points."""
    if n_bootstrap <= 0:
        raise ValueError("n_bootstrap must be positive.")
    if model_chunk_size <= 0:
        raise ValueError("model_chunk_size must be positive.")

    rng = np.random.default_rng(seed)
    n_questions, n_models = correctness.shape
    bootstrap_correct = np.zeros((n_bootstrap, n_models), dtype=np.int32)

    # A single set of sampled questions is shared across model columns.
    for indices in strata:
        n_stratum = len(indices)
        stratum_correctness = correctness[indices]
        sampled_positions = rng.integers(
            0,
            n_stratum,
            size=(n_bootstrap, n_stratum),
            dtype=np.int32,
        )
        for start in range(0, n_models, model_chunk_size):
            stop = min(start + model_chunk_size, n_models)
            bootstrap_correct[:, start:stop] += stratum_correctness[
                sampled_positions, start:stop
            ].sum(axis=1, dtype=np.int32)

    return bootstrap_correct * (100.0 / n_questions)


def write_results(
    output_path: Path,
    models: list[str],
    correctness: np.ndarray,
    bootstrap_accuracy: np.ndarray,
    confidence_level: float,
) -> None:
    """Write ranked point estimates and percentile intervals."""
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be between 0 and 1.")

    alpha = 1.0 - confidence_level
    lower_q = 100.0 * alpha / 2.0
    upper_q = 100.0 * (1.0 - alpha / 2.0)
    lower, upper = np.percentile(
        bootstrap_accuracy, [lower_q, upper_q], axis=0, method="linear"
    )
    n_questions = correctness.shape[0]
    correct_counts = correctness.sum(axis=0, dtype=np.int64)
    accuracy = correct_counts * (100.0 / n_questions)
    order = sorted(range(len(models)), key=lambda index: (-accuracy[index], index))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "Rank",
                "Model",
                "Correct",
                "Total",
                "Accuracy (%)",
                "95% CI lower (%)",
                "95% CI upper (%)",
                "Overall accuracy, % (95% CI)",
            ]
        )
        for rank, model_index in enumerate(order, start=1):
            acc_text = f"{half_up(accuracy[model_index], 2):.2f}"
            lower_text = f"{half_up(lower[model_index], 2):.2f}"
            upper_text = f"{half_up(upper[model_index], 2):.2f}"
            writer.writerow(
                [
                    rank,
                    models[model_index],
                    int(correct_counts[model_index]),
                    n_questions,
                    acc_text,
                    lower_text,
                    upper_text,
                    f"{acc_text} ({lower_text}-{upper_text})",
                ]
            )


def main() -> None:
    args = parse_args()
    models, correctness, strata = load_correctness_matrix(
        args.input, args.sheet, args.expected_questions
    )
    bootstrap_accuracy = stratified_bootstrap_accuracy(
        correctness,
        strata.values(),
        args.n_bootstrap,
        args.seed,
        args.model_chunk_size,
    )
    write_results(
        args.output,
        models,
        correctness,
        bootstrap_accuracy,
        args.confidence_level,
    )
    print(f"Input: {args.input}")
    print(f"Questions: {correctness.shape[0]}")
    print(f"Models: {correctness.shape[1]}")
    print(f"Strata: {len(strata)}")
    print(f"Bootstrap replicates: {args.n_bootstrap}")
    print(f"Random seed: {args.seed}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
