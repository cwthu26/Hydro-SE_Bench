"""
Batch evaluation score calculation functionality for multiple models
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .benchmark import Benchmark
from .datasets import load_builtin_benchmark
from .excel_loader import load_predictions_from_excel, _read_csv_safe
from .scoring import _format_accuracy


# Standard columns (non-model columns) list
# Note: Includes both English and Chinese column names for compatibility
STANDARD_COLUMNS = {
    "ID", "id", "Id", "ID列", "id列",
    "Question", "question", "Question列", "题目", "问题", "问题列",
    "Answer", "answer", "Answer列", "答案", "标准答案", "正确答案",
    "Level", "level", "难度", "难度等级",
    "Type", "type", "题型", "题目类型",
    "Category", "category", "类别", "分类",
    "Token", "token", "token列", "token数量", "token长度",
}


def is_standard_column(col_name: str) -> bool:
    """Determine if a column is a standard column (non-model column)"""
    col_lower = str(col_name).lower()
    # Check if in standard columns list
    if col_name in STANDARD_COLUMNS:
        return True
    # Check if contains token keyword
    if "token" in col_lower:
        return True
    return False


def identify_model_columns(df: pd.DataFrame, verbose: bool = True) -> list[str]:
    """
    Identify model columns from DataFrame.
    
    Args:
        df: DataFrame read from Excel file
        verbose: Whether to output detailed information
    
    Returns:
        List of model column names
    """
    model_columns = []
    
    if verbose:
        print("=" * 80)
        print("Identifying model columns...")
        print("=" * 80)
    
    for col in df.columns:
        if is_standard_column(col):
            if verbose:
                print(f"  [Standard Column] {col} - Skipped")
            continue
        
        # Every non-metadata column is evaluated, including failed/empty responses.
        non_null_count = df[col].notna().sum()
        model_columns.append(col)
        if verbose:
            print(f"  [Model Column] {col} - Contains {non_null_count} nonempty responses")
    
    if verbose:
        print(f"\n✓ Identified {len(model_columns)} model columns:")
        for i, col in enumerate(model_columns, 1):
            non_null_count = df[col].notna().sum()
            print(f"  {i}. {col} ({non_null_count} answers)")
    
    return model_columns


def evaluate_all_models(
    excel_path: str | Path,
    *,
    benchmark: Benchmark | None = None,
    benchmark_name: str = "hydrosebench",
    id_col: str | None = None,
    output_dir: str | Path | None = None,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Batch evaluate scores for all models in CSV or Excel file.
    
    Args:
        excel_path: CSV or Excel file path
        benchmark: Benchmark object, if None then use built-in benchmark
        benchmark_name: If benchmark is None, use this name to load built-in benchmark
        id_col: ID column name, if None then auto-detect
        output_dir: Output directory, if None then don't save files
        verbose: Whether to output detailed information
    
    Returns:
        Dictionary containing evaluation results for all models
    """
    excel_path = Path(excel_path)
    if not excel_path.is_file():
        raise FileNotFoundError(f"File not found: {excel_path}")
    
    # Load benchmark
    if benchmark is None:
        if verbose:
            print(f"Loading built-in {benchmark_name} benchmark...")
        benchmark = load_builtin_benchmark(benchmark_name)
        if verbose:
            print(f"✓ Benchmark loaded, {len(benchmark.examples)} questions total\n")
    
    # Read file (supports CSV and Excel)
    file_ext = excel_path.suffix.lower()
    if verbose:
        file_type = "CSV" if file_ext == ".csv" else "Excel"
        print(f"Reading {file_type} file: {excel_path}")
    
    if file_ext == ".csv":
        # Use safe CSV reading function, supports multiple encodings and formats
        df = _read_csv_safe(excel_path)
    else:
        df = pd.read_excel(excel_path)
    
    if verbose:
        print(f"\nFile contains {len(df)} rows, {len(df.columns)} columns")
        print(f"All column names: {list(df.columns)}\n")
    
    # Identify model columns
    model_columns = identify_model_columns(
        df.drop(columns=[id_col]) if id_col in df.columns else df, verbose=verbose)
    
    if len(model_columns) == 0:
        raise ValueError(
            "No model columns identified. Please check file format.\n"
            "Hint: Model columns should contain answer data (e.g., A, B, C, D or A,B, etc.)"
        )
    
    # Determine ID column
    if id_col is None:
        for possible_id in ["ID", "id", "Id"]:
            if possible_id in df.columns:
                id_col = possible_id
                break
    
    if verbose:
        if id_col:
            print(f"\n✓ Using ID column for matching: {id_col}")
        else:
            print(f"\n⚠ ID column not found, will use row order for matching")
    
    # Calculate scores for each model column
    results = []
    errors = []
    
    if verbose:
        print("\n" + "=" * 80)
        print("Starting batch score calculation...")
        print("=" * 80)
    
    for model_col in model_columns:
        if verbose:
            print(f"\nProcessing model: {model_col}")
            print("-" * 80)
        
        try:
            # Load predictions for this model
            predictions = load_predictions_from_excel(
                excel_path,
                id_col=id_col,
                answer_col=model_col
            )
            
            # Calculate scores
            report = benchmark.score(predictions)
            
            # Statistics
            correct_count = sum(1 for s in report.example_scores if s.is_correct)
            incorrect_count = report.incorrect_count
            missing_count = sum(1 for s in report.example_scores if s.missing_prediction)
            
            # Statistics by category, level, and type
            category_stats = report.get_category_stats(benchmark) if benchmark else {}
            level_stats = report.get_level_stats(benchmark) if benchmark else {}
            type_stats = report.get_type_stats(benchmark) if benchmark else {}
            
            # Save result
            result = {
                "model_name": model_col,
                "total_score": report.total_score,
                "max_score": report.max_score,
                "accuracy": report.accuracy,
                "correct_count": correct_count,
                "incorrect_count": incorrect_count,
                "missing_count": missing_count,
                "total_questions": report.total_questions,
                "unscored_count": report.unscored_count,
                "issue_counts": report.issue_counts,
                "issues": report.issues,
                "category_stats": category_stats,
                "level_stats": level_stats,
                "type_stats": type_stats,
            }
            results.append(result)
            
            if verbose:
                print(f"  Total score: {report.total_score}/{report.max_score}")
                print(f"  Accuracy: {_format_accuracy(report.accuracy)}")
                print(f"  Correct: {correct_count}, Incorrect: {incorrect_count}, Unscored: {report.unscored_count}")
            
            # Save detailed reports (JSON and Excel)
            if output_dir:
                output_dir_path = Path(output_dir)
                output_dir_path.mkdir(parents=True, exist_ok=True)
                
                # Generate safe folder name (for creating folder)
                safe_name = model_col.replace("/", "_").replace("\\", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_")
                
                # Create separate folder for each model
                model_dir = output_dir_path / safe_name
                model_dir.mkdir(parents=True, exist_ok=True)
                
                # Save JSON report
                json_file = model_dir / "score_report.json"
                json_file.write_text(report.to_json(), encoding="utf-8")
                report.to_issues_csv(model_dir / "score_report_issues.csv")
                
                # Save CSV report (lightweight, recommended)
                csv_file = model_dir / "score_report.csv"
                try:
                    report.to_csv(csv_file, benchmark=benchmark)
                    if verbose:
                        print(f"  ✓ CSV report: {csv_file}")
                except ImportError:
                    if verbose:
                        print(f"  ⚠ Hint: Install pandas to generate CSV report")
                
                # Save Excel report (more intuitive, optional)
                excel_file = model_dir / "score_report.xlsx"
                try:
                    report.to_excel(excel_file, benchmark=benchmark)
                    if verbose:
                        print(f"  ✓ Excel report: {excel_file}")
                except ImportError:
                    if verbose:
                        print(f"  ⚠ Hint: Install pandas and openpyxl to generate Excel report")
                
                if verbose:
                    print(f"  ✓ Detailed reports saved to folder: {safe_name}/")
            
        except Exception as e:
            error_info = {
                "model_name": model_col,
                "error": str(e)
            }
            errors.append(error_info)
            if verbose:
                print(f"  ❌ Processing failed: {e}")
    
    # Sort by accuracy
    sorted_results = sorted(results, key=lambda x: x["accuracy"] if x["accuracy"] is not None else -1, reverse=True)
    
    # Summary results
    summary = {
        "benchmark": benchmark_name,
        "total_questions": len(benchmark.examples),
        "models_count": len(model_columns),
        "model_columns": model_columns,
        "results": sorted_results,
        "errors": errors if errors else None,
    }
    
    # Save summary results
    if output_dir:
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        summary_file = output_dir_path / "all_models_summary.json"
        summary_file.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        if verbose:
            print(f"\n✓ Summary results saved to: {summary_file}")
    
    # Output summary
    if verbose:
        print("\n" + "=" * 80)
        print("All Models Score Summary")
        print("=" * 80)
        print(f"{'Model Name':<40} {'Total Score':<15} {'Accuracy':<15} {'Correct/Incorrect/Unscored':<25}")
        print("-" * 80)
        
        for result in sorted_results:
            score_str = f"{result['total_score']}/{result['max_score']}"
            accuracy_str = _format_accuracy(result['accuracy'])
            detail_str = f"{result['correct_count']}/{result['incorrect_count']}/{result['unscored_count']}"
            print(f"{result['model_name']:<40} {score_str:<15} {accuracy_str:<15} {detail_str:<25}")
        
        if errors:
            print("\nFailed models:")
            for error in errors:
                print(f"  {error['model_name']}: {error['error']}")
        
        print("\n" + "=" * 80)
        print("Batch calculation completed!")
        print("=" * 80)
        print(f"\nProcessed {len(model_columns)} models")
        if output_dir:
            print(f"Results saved to: {output_dir_path}")
    
    return summary

