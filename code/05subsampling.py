#!/usr/bin/env python3
"""Analyze accuracy stability under stratified question subsampling.

Questions are sampled without replacement within each category_sheet x Task
(level A/B/C) stratum, using the same seed and rounding rule as the released
sampling analysis. The same subset is evaluated for every model column. Each
subsampled accuracy is compared with that model's full-benchmark accuracy for
the same Task. The two-model mean and standard-deviation series used for
Fig. 7 are also reported. The 100% subset is deterministic.

Outputs: one Fig. 7 CSV and two tolerance-analysis CSVs. No figure is
produced. Requires Python 3.10+, numpy, and openpyxl.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from collections import OrderedDict
from pathlib import Path

import numpy as np
from openpyxl import load_workbook


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "hydrobench_final_model_answer_table.xlsx"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "subsampling_results"
METADATA_COLUMNS = {"row_index", "custom_id", "id", "category_sheet", "level",
                    "type", "question", "gold_answer"}
TASKS = ("A", "B", "C")
RATIOS = tuple(range(10, 101, 10))
FIGURE_MODELS = ("DeepSeek-V3.2-Exp", "Claude Sonnet 4.5")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--trials", type=int, default=100,
                        help="Subsets per ratio below 100%% (default: 100).")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tolerance-pp", type=float, default=5.0,
                        help="Maximum absolute accuracy difference in percentage points.")
    parser.add_argument("--figure-models", nargs="+", default=list(FIGURE_MODELS),
                        help="Model columns for the Fig. 7 accuracy series.")
    return parser.parse_args()


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def model_names(path: Path) -> list[str]:
    """Use the model-answer columns in the supplied results worksheet."""
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if "results" not in workbook:
            raise ValueError("Missing results sheet")
        headers = [clean(value) for value in next(workbook["results"].values)]
        if len(headers) != len(set(headers)):
            raise ValueError("Duplicate column names in results sheet")
        models = [name for name in headers if name not in METADATA_COLUMNS]
        if not models:
            raise ValueError("No model-answer columns found")
        return models
    finally:
        workbook.close()


def load_data(path: Path, models: list[str]):
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if "results" not in workbook:
            raise ValueError("Missing results sheet")
        rows = workbook["results"].values
        headers = [clean(value) for value in next(rows)]
        required = ["category_sheet", "level", "gold_answer", *models]
        missing = [name for name in required if name not in headers]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
        columns = {name: headers.index(name) for name in required}
        groups: OrderedDict[str, dict[str, list[int]]] = OrderedDict()
        correctness: list[list[bool]] = []
        for row_number, row in enumerate(rows, start=2):
            if not any(value is not None for value in row):
                continue
            category = clean(row[columns["category_sheet"]])
            task = clean(row[columns["level"]])
            gold = clean(row[columns["gold_answer"]])
            if not category or task not in TASKS or not gold:
                raise ValueError(f"Invalid category_sheet, level or gold_answer at row {row_number}")
            index = len(correctness)
            groups.setdefault(category, {name: [] for name in TASKS})[task].append(index)
            correctness.append([bool(clean(row[columns[model]]))
                                and clean(row[columns[model]]) == gold for model in models])
        if not correctness or any(not any(group[t] for group in groups.values()) for t in TASKS):
            raise ValueError("Missing question rows or a Task category")
        return np.asarray(correctness, dtype=np.bool_), groups
    finally:
        workbook.close()


def sampled_indices(groups, ratio: int, trial: int, seed: int) -> dict[str, np.ndarray]:
    """Sample without replacement within each subfield and Task stratum."""
    selected = {task: [] for task in TASKS}
    for category_index, task_groups in enumerate(groups.values()):
        for task in TASKS:
            indices = np.asarray(task_groups[task], dtype=np.int64)
            if indices.size == 0:
                continue
            count = max(1, indices.size * ratio // 100)
            if count == indices.size:
                draw = indices
            else:
                stratum_seed = seed + trial + category_index * 1000 + ord(task)
                draw = np.random.RandomState(stratum_seed).choice(
                    indices, size=count, replace=False)
            selected[task].append(draw)
    return {task: np.concatenate(parts) for task, parts in selected.items()}


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    args = parse_args()
    if args.trials < 1 or args.seed < 0 or args.tolerance_pp < 0:
        raise ValueError("Trials must be positive; seed and tolerance must be nonnegative")
    models = model_names(args.input)
    missing_figure_models = [model for model in args.figure_models if model not in models]
    if missing_figure_models:
        raise ValueError(f"Unknown figure models: {missing_figure_models}")
    correctness, groups = load_data(args.input, models)
    full_indices = sampled_indices(groups, 100, 0, args.seed)
    full_accuracy = {task: 100 * correctness[indices].mean(axis=0)
                     for task, indices in full_indices.items()}
    input_sha256 = hashlib.sha256(args.input.read_bytes()).hexdigest()
    detail: list[dict[str, object]] = []
    summary: list[dict[str, object]] = []
    figure: list[dict[str, object]] = []

    for ratio in RATIOS:
        n_draws = 1 if ratio == 100 else args.trials
        observed = {task: np.empty((n_draws, len(models)), dtype=float) for task in TASKS}
        observed_total = np.empty((n_draws, len(models)), dtype=float)
        subset_sizes = {}
        for trial in range(n_draws):
            indices_by_task = sampled_indices(groups, ratio, trial, args.seed)
            for task, indices in indices_by_task.items():
                subset_sizes[task] = len(indices)
                observed[task][trial] = 100 * correctness[indices].mean(axis=0)
            total_indices = np.concatenate([indices_by_task[task] for task in TASKS])
            observed_total[trial] = 100 * correctness[total_indices].mean(axis=0)
        total_questions = sum(subset_sizes.values())
        for model in args.figure_models:
            column = models.index(model)
            for task in (*TASKS, "Total"):
                values = observed_total[:, column] if task == "Total" else observed[task][:, column]
                figure.append({
                    "model": model, "sample_ratio_percent": ratio,
                    "level": task,
                    "n_questions": total_questions if task == "Total" else subset_sizes[task],
                    "mean_accuracy_percent": f"{values.mean():.2f}",
                    "std_accuracy_percent": f"{values.std(ddof=0):.2f}",
                    "n_trials": args.trials,
                })
        for task in TASKS:
            errors = np.abs(observed[task] - full_accuracy[task])
            passed = errors <= args.tolerance_pp + 1e-12
            counts = passed.sum(axis=0)
            model_rates = 100 * counts / n_draws
            for column, model in enumerate(models):
                detail.append({
                    "model": model, "task": f"Task {task}",
                    "sample_ratio_percent": ratio,
                    "full_task_questions": len(full_indices[task]),
                    "subset_task_questions": subset_sizes[task],
                    "full_accuracy_percent": f"{full_accuracy[task][column]:.6f}",
                    "tolerance_percentage_points": args.tolerance_pp,
                    "n_subsets": n_draws,
                    "n_within_tolerance": int(counts[column]),
                    "pass_rate_percent": f"{model_rates[column]:.2f}",
                    "mean_absolute_error_pp": f"{errors[:, column].mean():.4f}",
                    "max_absolute_error_pp": f"{errors[:, column].max():.4f}",
                    "random_seed": args.seed, "input_sha256": input_sha256,
                })
            summary.append({
                "task": f"Task {task}", "sample_ratio_percent": ratio,
                "tolerance_percentage_points": args.tolerance_pp,
                "n_models": len(models), "n_subsets_per_model": n_draws,
                "model_subset_comparisons": int(passed.size),
                "n_within_tolerance": int(passed.sum()),
                "pooled_pass_rate_percent": f"{100 * passed.mean():.2f}",
                "models_with_all_subsets_within_tolerance": int((counts == n_draws).sum()),
                "models_with_pass_rate_at_least_95_percent": int((model_rates >= 95).sum()),
                "min_model_pass_rate_percent": f"{model_rates.min():.2f}",
                "median_model_pass_rate_percent": f"{np.median(model_rates):.2f}",
                "max_model_pass_rate_percent": f"{model_rates.max():.2f}",
                "random_seed": args.seed, "input_sha256": input_sha256,
            })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    detail_path = args.output_dir / "subsampling_task_tolerance_by_model.csv"
    summary_path = args.output_dir / "subsampling_task_tolerance_summary.csv"
    figure_path = args.output_dir / "subsampling_accuracy.csv"
    write_csv(detail_path, detail)
    write_csv(summary_path, summary)
    write_csv(figure_path, figure)
    print(f"Analyzed {len(correctness)} questions, {len(models)} models, "
          f"{args.trials} draws per ratio below 100%, tolerance +/-{args.tolerance_pp} pp")
    print(detail_path)
    print(summary_path)
    print(figure_path)


if __name__ == "__main__":
    main()
