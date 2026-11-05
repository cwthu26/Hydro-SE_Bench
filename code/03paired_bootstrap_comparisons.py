#!/usr/bin/env python3
"""Calculate paired accuracy comparisons for the leading models.

The script reads ``hydrobench_final_model_answer_table.xlsx`` from the same
directory as this file by default. It selects the eight models with the
highest observed overall accuracy, applies the same subfield-by-task-level-by-format
stratified bootstrap samples to every model, and reports all 28 unique paired
comparisons. Two-sided bootstrap P values are adjusted by the Holm procedure.

Dependencies: numpy, openpyxl
"""

from __future__ import annotations

import argparse
import csv
from collections import OrderedDict
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations
from pathlib import Path
from typing import Iterable

import numpy as np
from openpyxl import load_workbook


DEFAULT_INPUT_NAME = "hydrobench_final_model_answer_table.xlsx"
DEFAULT_OUTPUT_NAME = "Paired_bootstrap_comparisons.csv"
DEFAULT_SHEET = "results"
DEFAULT_BOOTSTRAPS = 10_000
DEFAULT_SEED = 42
DEFAULT_CONFIDENCE_LEVEL = 0.95
DEFAULT_TOP_MODELS = 8
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
            "Calculate subfield-by-level-by-format stratified paired bootstrap "
            "comparisons for Supplementary Table 3."
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
        "--top-models",
        type=int,
        default=DEFAULT_TOP_MODELS,
        help="Number of leading models included (default: 8).",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        help="Optional explicit model list; overrides --top-models.",
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
    """Return paired bootstrap model accuracies in percentage points."""
    if n_bootstrap <= 0:
        raise ValueError("n_bootstrap must be positive.")
    if model_chunk_size <= 0:
        raise ValueError("model_chunk_size must be positive.")

    rng = np.random.default_rng(seed)
    n_questions, n_models = correctness.shape
    bootstrap_correct = np.zeros((n_bootstrap, n_models), dtype=np.int32)

    # Every model is evaluated on the same sampled questions in each replicate.
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


def centered_bootstrap_p_value(
    bootstrap_difference: np.ndarray,
    observed_difference: float,
) -> float:
    """Calculate a two-sided centered-bootstrap P value.

    The bootstrap distribution is centered at the observed estimate to form
    the null distribution. A plus-one correction prevents zero P values.
    """
    null_difference = bootstrap_difference - observed_difference
    extreme = np.count_nonzero(
        np.abs(null_difference) >= abs(observed_difference)
    )
    return float((extreme + 1) / (len(bootstrap_difference) + 1))


def holm_adjust(p_values: list[float]) -> list[float]:
    """Apply the step-down Holm family-wise error correction."""
    count = len(p_values)
    order = sorted(range(count), key=lambda index: p_values[index])
    adjusted = [0.0] * count
    running_maximum = 0.0
    for rank, original_index in enumerate(order):
        candidate = min(1.0, (count - rank) * p_values[original_index])
        running_maximum = max(running_maximum, candidate)
        adjusted[original_index] = running_maximum
    return adjusted


def choose_models(
    all_models: list[str],
    correctness: np.ndarray,
    explicit_models: list[str] | None,
    top_models: int,
) -> tuple[list[str], np.ndarray]:
    """Select explicit models or the leading models by observed accuracy."""
    if explicit_models:
        missing = [model for model in explicit_models if model not in all_models]
        if missing:
            raise ValueError(f"Unknown model names: {missing}")
        indices = [all_models.index(model) for model in explicit_models]
    else:
        if top_models < 2 or top_models > len(all_models):
            raise ValueError(
                f"top_models must be between 2 and {len(all_models)}."
            )
        accuracy = correctness.mean(axis=0)
        indices = sorted(
            range(len(all_models)), key=lambda index: (-accuracy[index], index)
        )[:top_models]
    return [all_models[index] for index in indices], correctness[:, indices]


def write_results(
    output_path: Path,
    models: list[str],
    correctness: np.ndarray,
    bootstrap_accuracy: np.ndarray,
    confidence_level: float,
) -> None:
    """Write every unique paired comparison and Holm-adjusted P value."""
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be between 0 and 1.")

    alpha = 1.0 - confidence_level
    lower_q = 100.0 * alpha / 2.0
    upper_q = 100.0 * (1.0 - alpha / 2.0)
    observed_accuracy = correctness.mean(axis=0) * 100.0

    comparisons: list[dict[str, object]] = []
    raw_p_values: list[float] = []
    for first, second in combinations(range(len(models)), 2):
        observed_difference = observed_accuracy[first] - observed_accuracy[second]
        bootstrap_difference = (
            bootstrap_accuracy[:, first] - bootstrap_accuracy[:, second]
        )
        lower, upper = np.percentile(
            bootstrap_difference, [lower_q, upper_q], method="linear"
        )
        p_value = centered_bootstrap_p_value(
            bootstrap_difference, observed_difference
        )
        raw_p_values.append(p_value)
        comparisons.append(
            {
                "model_1": models[first],
                "model_2": models[second],
                "accuracy_1": observed_accuracy[first],
                "accuracy_2": observed_accuracy[second],
                "difference": observed_difference,
                "ci_lower": float(lower),
                "ci_upper": float(upper),
                "p_value": p_value,
            }
        )

    adjusted_p_values = holm_adjust(raw_p_values)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "Model 1",
                "Model 2",
                "Accuracy 1 (%)",
                "Accuracy 2 (%)",
                "Difference (pp)",
                "95% paired bootstrap CI lower (pp)",
                "95% paired bootstrap CI upper (pp)",
                "95% paired bootstrap CI (pp)",
                "Bootstrap P",
                "Holm-adjusted P",
                "Holm-adjusted P < 0.05",
            ]
        )
        for comparison, adjusted_p in zip(comparisons, adjusted_p_values):
            accuracy_1 = f"{half_up(float(comparison['accuracy_1']), 2):.2f}"
            accuracy_2 = f"{half_up(float(comparison['accuracy_2']), 2):.2f}"
            difference = f"{half_up(float(comparison['difference']), 2):.2f}"
            lower = f"{half_up(float(comparison['ci_lower']), 2):.2f}"
            upper = f"{half_up(float(comparison['ci_upper']), 2):.2f}"
            writer.writerow(
                [
                    comparison["model_1"],
                    comparison["model_2"],
                    accuracy_1,
                    accuracy_2,
                    difference,
                    lower,
                    upper,
                    f"{lower} to {upper}",
                    f"{float(comparison['p_value']):.6f}",
                    f"{adjusted_p:.3f}",
                    "Yes" if adjusted_p < 0.05 else "No",
                ]
            )


def main() -> None:
    args = parse_args()
    all_models, all_correctness, strata = load_correctness_matrix(
        args.input, args.sheet, args.expected_questions
    )
    models, correctness = choose_models(
        all_models, all_correctness, args.models, args.top_models
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
    print(f"Models compared: {', '.join(models)}")
    print(f"Pairwise comparisons: {len(models) * (len(models) - 1) // 2}")
    print(f"Strata: {len(strata)}")
    print(f"Bootstrap replicates: {args.n_bootstrap}")
    print(f"Random seed: {args.seed}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
