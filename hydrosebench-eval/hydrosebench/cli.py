from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .benchmark import Benchmark
from .datasets import BUILTIN_BENCHMARKS, download_hydrosebench_data, load_builtin_benchmark
from .excel_loader import load_benchmark_from_file, load_predictions_from_excel
from .batch_evaluate import evaluate_all_models


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hydrosebench",
        description="Score model predictions on the HydroSEBench benchmark.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    eval_parser = subparsers.add_parser("evaluate", help="Score a predictions file")
    eval_parser.add_argument(
        "--benchmark",
        choices=sorted(BUILTIN_BENCHMARKS),
        help="Use a bundled benchmark (hydrosebench).",
    )
    eval_parser.add_argument(
        "--benchmark-path",
        type=Path,
        help="Path to a benchmark JSON, CSV, or Excel file (overrides --benchmark).",
    )
    eval_parser.add_argument(
        "--benchmark-excel",
        type=Path,
        help="Path to a benchmark CSV or Excel file (alternative to --benchmark-path).",
    )
    eval_parser.add_argument(
        "--predictions",
        type=Path,
        required=True,
        help="JSON, CSV, or Excel file containing model outputs.",
    )
    eval_parser.add_argument(
        "--predictions-id-col",
        type=str,
        default="ID",
        help="Column name for question IDs in predictions Excel. If not specified and Excel has 'ID' column, will use it. Set to empty string to disable ID matching and use row order instead.",
    )
    eval_parser.add_argument(
        "--predictions-answer-col",
        type=str,
        default="Answer",
        help="Column name for answers in predictions Excel (default: Answer).",
    )
    eval_parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write a report. Supports .json, .csv, .xlsx, and .md formats.",
    )
    eval_parser.add_argument(
        "--output-format",
        choices=["json", "csv", "xlsx", "md", "auto"],
        default="auto",
        help="Output format. 'auto' detects from file extension (default: auto).",
    )
    eval_parser.add_argument(
        "--show-details",
        action="store_true",
        help="Print per-question correctness to stdout.",
    )

    # Batch evaluation command
    batch_parser = subparsers.add_parser(
        "batch-evaluate",
        help="Batch evaluate multiple models from an Excel file",
    )
    batch_parser.add_argument(
        "--excel",
        type=Path,
        required=True,
        help="CSV or Excel file containing predictions from multiple models.",
    )
    batch_parser.add_argument(
        "--benchmark",
        choices=sorted(BUILTIN_BENCHMARKS),
        default="hydrosebench",
        help="Use a bundled benchmark (default: hydrosebench).",
    )
    batch_parser.add_argument(
        "--benchmark-path",
        type=Path,
        help="Path to a benchmark JSON, CSV, or Excel file (overrides --benchmark).",
    )
    batch_parser.add_argument(
        "--id-col",
        type=str,
        help="Column name for question IDs (default: auto-detect).",
    )
    batch_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to save detailed reports (default: same as Excel file directory).",
    )
    batch_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output.",
    )

    # Download command
    download_parser = subparsers.add_parser(
        "download",
        help="Download hydrosebench data files (JSON or CSV)",
    )
    download_parser.add_argument(
        "--format",
        choices=["json", "csv", "all"],
        default="all",
        help="File format to download: json, csv, or all (default: all)",
    )
    download_parser.add_argument(
        "--output",
        type=Path,
        help="Output directory or file path. If directory, files will be saved there. If file path, only single format can be specified. Default: current directory",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "evaluate":
        benchmark = _load_benchmark(args)
        predictions_payload = _load_predictions(args)

        report = benchmark.score(predictions_payload)
        print(report.summary())
        if report.issue_counts:
            print("Unscored reasons: " + ", ".join(f"{key}={value}" for key, value in report.issue_counts.items()))

        if args.show_details:
            for score in report.example_scores:
                print(f"{score.status} {score.example_id}: expected {score.expected}, predicted {score.predicted}; {score.reason}")

        if args.output:
            output_path = Path(args.output)
            output_format = args.output_format
            
            # Auto-detect format
            if output_format == "auto":
                ext = output_path.suffix.lower()
                if ext == ".csv":
                    output_format = "csv"
                elif ext == ".xlsx":
                    output_format = "xlsx"
                elif ext == ".md" or ext == ".markdown":
                    output_format = "md"
                else:
                    output_format = "json"
            
            # Export report
            if output_format == "csv":
                report.to_csv(output_path, benchmark=benchmark)
                print(f"CSV report saved to: {output_path}")
            elif output_format == "xlsx":
                report.to_excel(output_path, benchmark=benchmark)
                print(f"Excel report saved to: {output_path}")
            elif output_format == "md":
                report.to_markdown(output_path, benchmark=benchmark)
                print(f"Markdown report saved to: {output_path}")
            else:
                output_path.write_text(report.to_json(), encoding="utf-8")
                print(f"JSON report saved to: {output_path}")
            issues_path = output_path.with_name(output_path.stem + "_issues.csv")
            report.to_issues_csv(issues_path)
            print(f"Issue details saved to: {issues_path}")

        return 0

    elif args.command == "batch-evaluate":
        # Load benchmark
        if args.benchmark_path:
            path = args.benchmark_path
            if path.suffix.lower() in (".csv", ".xlsx", ".xls", ".excel"):
                benchmark = load_benchmark_from_file(path)
            else:
                benchmark = Benchmark.from_file(path)
        else:
            benchmark = load_builtin_benchmark(args.benchmark)

        # Determine output directory
        output_dir = args.output_dir
        if output_dir is None:
            output_dir = args.excel.parent

        # Execute batch evaluation
        summary = evaluate_all_models(
            args.excel,
            benchmark=benchmark,
            id_col=args.id_col,
            output_dir=output_dir,
            verbose=not args.quiet,
        )

        return 1 if summary["errors"] else 0

    elif args.command == "download":
        # Determine output path
        if args.output is None:
            output_path = Path.cwd()
        else:
            output_path = Path(args.output)

        # If output path is a file, only support single format
        if output_path.is_file() or (args.format != "all" and output_path.suffix):
            if args.format == "all":
                raise SystemExit(
                    "Cannot download all formats to a single file. "
                    "Please specify --format json or --format csv, or use a directory path."
                )
            # Download to specified file path
            downloaded_path = download_hydrosebench_data(args.format, output_path)
            print(f"File downloaded to: {downloaded_path}")
        else:
            # Output path is a directory
            output_path.mkdir(parents=True, exist_ok=True)
            
            if args.format in ("json", "all"):
                json_path = download_hydrosebench_data("json", output_path / "hydrosebench.json")
                print(f"JSON file downloaded to: {json_path}")
            
            if args.format in ("csv", "all"):
                csv_path = download_hydrosebench_data("csv", output_path / "hydrosebench.csv")
                print(f"CSV file downloaded to: {csv_path}")

        return 0

    else:  # pragma: no cover - future-proof
        parser.error("Unknown command")
        return 1


def _load_benchmark(args: argparse.Namespace) -> Benchmark:
    if args.benchmark_excel:
        return load_benchmark_from_file(args.benchmark_excel)
    if args.benchmark_path:
        path = args.benchmark_path
        if path.suffix.lower() in (".csv", ".xlsx", ".xls", ".excel"):
            return load_benchmark_from_file(path)
        return Benchmark.from_file(path)
    if args.benchmark:
        return load_builtin_benchmark(args.benchmark)
    raise SystemExit("Please provide --benchmark, --benchmark-path, or --benchmark-excel")


def _load_predictions(args: argparse.Namespace) -> Any:
    path = args.predictions
    if path.suffix.lower() in (".csv", ".xlsx", ".xls", ".excel"):
        # If id_col is specified as empty string, use None (order by row)
        id_col = args.predictions_id_col if args.predictions_id_col else None
        # If id_col is "ID" but Excel doesn't have this column, automatically downgrade to None (order by row)
        if id_col == "ID":
            import pandas as pd
            try:
                df = pd.read_excel(path, nrows=0)  # Only read column names
                if "ID" not in df.columns:
                    id_col = None
            except Exception:
                pass  # If read fails, continue using "ID"
        
        return load_predictions_from_excel(
            path,
            id_col=id_col,
            answer_col=args.predictions_answer_col,
        )
    # JSON file
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:  # pragma: no cover - user input
        raise SystemExit(f"Cannot parse prediction file {path}: {exc}") from exc

