"""
Example 5: Complete Workflow
Demonstrates data validation, optional sampling, batch evaluation, analysis, and report generation.
"""

from utils import setup_package_path, get_output_dir, get_test_data_path
from pathlib import Path

# Setup package path
PROJECT_ROOT = setup_package_path()

from hydrosebench import (
    evaluate_all_models,
    load_benchmark_from_file,
    create_summary_excel,
    identify_model_columns,
    sample_benchmark_by_category,
    validate_data_quality,
    generate_analysis_report,
)
from hydrosebench.excel_loader import _read_csv_safe, _detect_file_format
import pandas as pd


def main():
    """Complete workflow example"""
    print("=" * 80)
    print("Example 5: Complete Workflow")
    print("=" * 80)
    print("This example demonstrates: Data Validation → Sampling → Evaluation → Deep Analysis → Report Generation")
    print("=" * 80)
    print()
    
    # ========== Phase 1: Data Preparation and Validation ==========
    print("【Phase 1】Data Preparation and Validation")
    print("-" * 80)
    
    excel_path = get_test_data_path(PROJECT_ROOT)
    output_dir = get_output_dir(PROJECT_ROOT, "example_5_complete_workflow")
    
    if not excel_path.exists():
        print(f"⚠ Example file does not exist: {excel_path}")
        print("Please ensure test.csv or test.xlsx exists, or modify excel_path to point to your data file")
        return
    
    print(f"Input file: {excel_path}")
    print(f"Output directory: {output_dir}")
    print()
    
    # 1.1 Load benchmark
    print("Step 1.1: Loading benchmark...")
    benchmark = load_benchmark_from_file(excel_path)
    print(f"✓ Benchmark loaded, {len(benchmark.examples)} questions total")
    
    # Statistics of benchmark information
    category_counts = {}
    level_counts = {}
    for ex in benchmark.examples:
        category_counts[ex.category] = category_counts.get(ex.category, 0) + 1
        if ex.level:
            level_counts[ex.level] = level_counts.get(ex.level, 0) + 1
    
    print(f"  - Category distribution: {dict(sorted(category_counts.items()))}")
    if level_counts:
        print(f"  - Difficulty distribution: {dict(sorted(level_counts.items()))}")
    print()
    
    # 1.2 Preview and validate data
    print("Step 1.2: Previewing and validating prediction data...")
    # Safely read file based on file format
    file_ext = excel_path.suffix.lower()
    actual_format = _detect_file_format(excel_path)
    
    # If extension is .csv but actual format is Excel, use Excel reading method
    if file_ext == ".csv" and actual_format == 'excel':
        print(f"  ⚠ Warning: File extension is .csv, but detected actual format is Excel. Will use Excel reading method.")
        df = pd.read_excel(excel_path, engine='openpyxl')
    elif file_ext == ".csv":
        df = _read_csv_safe(excel_path)
    elif file_ext in (".xlsx", ".xls"):
        # Try using openpyxl engine (.xlsx) or xlrd engine (.xls)
        try:
            if file_ext == ".xlsx":
                df = pd.read_excel(excel_path, engine='openpyxl')
            else:
                df = pd.read_excel(excel_path, engine='xlrd')
        except Exception:
            # If specified engine fails, let pandas auto-select
            df = pd.read_excel(excel_path)
    else:
        # If extension is not supported, but detected as Excel format, try using Excel reading
        if actual_format == 'excel':
            print(f"  ⚠ Warning: File extension is {file_ext}, but detected actual format is Excel. Will try using Excel reading method.")
            try:
                df = pd.read_excel(excel_path, engine='openpyxl')
            except Exception:
                df = pd.read_excel(excel_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}. Supported formats: .csv, .xlsx, .xls")
    
    print(f"  - Data rows: {len(df)}")
    print(f"  - Total columns: {len(df.columns)}")
    
    # Data quality check
    quality_report = validate_data_quality(df, benchmark)
    print(f"  - Identified {quality_report['model_count']} model columns")
    
    if quality_report["issues"]:
        print("  ⚠ Found critical issues:")
        for issue in quality_report["issues"]:
            print(f"    - {issue}")
    
    if quality_report["warnings"]:
        print("  ⚠ Warning messages:")
        for warning in quality_report["warnings"]:
            print(f"    - {warning}")
    
    if not quality_report["issues"]:
        print("  ✓ Data quality check passed")
    print()
    
    # ========== Phase 2: Sampling to Create Subset (Optional) ==========
    print("【Phase 2】Sampling to Create Test Subset (Optional)")
    print("-" * 80)
    
    use_sampled = False  # Can be set to True to use sampled subset
    if use_sampled:
        print("Step 2.1: Creating sampled subset...")
        sampled_benchmark = sample_benchmark_by_category(
            benchmark,
            per_category=5,
            seed=42,
            output_path=output_dir / f"sampled_benchmark{excel_path.suffix}",
        )
        benchmark = sampled_benchmark
        print(f"✓ Sampled subset created, {len(benchmark.examples)} questions total")
        print()
    else:
        print("  (Skipping sampling, using full benchmark)")
        print()
    
    # ========== Phase 3: Batch Evaluation ==========
    print("【Phase 3】Batch Evaluation of All Models")
    print("-" * 80)
    
    print("Step 3.1: Identifying model columns...")
    model_columns = identify_model_columns(df, verbose=True)
    print()
    
    if not model_columns:
        print("⚠ No model columns identified, please check Excel file format")
        return
    
    # Keep all rows so missing standard answers and model answers are reported
    
    print("Step 3.2: Executing batch evaluation...")
    summary = evaluate_all_models(
        excel_path,
        benchmark=benchmark,
        output_dir=output_dir,
        verbose=True,
    )
    
    print()
    
    # ========== Phase 4: Generate Summary Report ==========
    print("【Phase 4】Generate Summary Report")
    print("-" * 80)
    
    print("Step 4.1: Generating model comparison Excel...")
    create_summary_excel(summary, output_dir, benchmark)
    print("✓ Model comparison summary Excel generated")
    print()
    
    # ========== Phase 5: Deep Analysis ==========
    print("【Phase 5】Deep Data Analysis")
    print("-" * 80)
    
    # Check if there are results
    if not summary["results"]:
        print("⚠ No successfully evaluated models, cannot perform deep analysis")
        if summary.get("errors"):
            print("\nFailed models:")
            for error in summary["errors"]:
                print(f"  - {error['model_name']}: {error['error']}")
        return
    
    # 5.1 Basic statistical analysis
    print("Step 5.1: Basic statistical analysis...")
    scored_results = [r for r in summary["results"] if r["accuracy"] is not None]
    if scored_results:
        best_model = scored_results[0]
        worst_model = scored_results[-1]
        avg_accuracy = sum(r["accuracy"] for r in scored_results) / len(scored_results)
        print(f"  🏆 Best model: {best_model['model_name']} ({best_model['accuracy']:.2%})")
        print(f"  📉 Worst model: {worst_model['model_name']} ({worst_model['accuracy']:.2%})")
        print(f"  📊 Average accuracy: {avg_accuracy:.2%}")
        print(f"  📈 Accuracy standard deviation: {pd.Series([r['accuracy'] for r in scored_results]).std():.4f}")
    else:
        print("  Accuracy: N/A; no scorable responses. See the per-model issue reports.")
    print()
    
    # 5.2 Category analysis
    print("Step 5.2: Category dimension analysis...")
    if any(r.get("category_stats") for r in summary["results"]):
        all_categories = set()
        for result in summary["results"]:
            if result.get("category_stats"):
                all_categories.update(result["category_stats"].keys())
        
        print("  Best performance by category:")
        for category in sorted(all_categories):
            best_acc = 0
            best_model_name = ""
            worst_acc = 1.0
            worst_model_name = ""
            
            for result in summary["results"]:
                stats = result.get("category_stats", {}).get(category, {})
                if stats and stats.get("accuracy") is not None:
                    acc = stats.get("accuracy", 0)
                    if acc > best_acc:
                        best_acc = acc
                        best_model_name = result["model_name"]
                    if acc < worst_acc:
                        worst_acc = acc
                        worst_model_name = result["model_name"]
            
            print(f"    {category}:")
            if not any(r.get("category_stats", {}).get(category, {}).get("accuracy") is not None for r in summary["results"]):
                print("      Accuracy: N/A; no scorable responses")
                continue
            print(f"      Best: {best_model_name} ({best_acc:.2%})")
            print(f"      Worst: {worst_model_name} ({worst_acc:.2%})")
            print(f"      Gap: {(best_acc - worst_acc):.2%}")
    print()
    
    # 5.3 Difficulty analysis
    print("Step 5.3: Difficulty dimension analysis...")
    if any(r.get("level_stats") for r in summary["results"]):
        all_levels = set()
        for result in summary["results"]:
            if result.get("level_stats"):
                all_levels.update(result["level_stats"].keys())
        
        print("  Average performance by difficulty level:")
        for level in sorted(all_levels):
            level_accuracies = []
            for result in summary["results"]:
                stats = result.get("level_stats", {}).get(level, {})
                if stats and stats.get("accuracy") is not None:
                    level_accuracies.append(stats.get("accuracy", 0))
            
            if level_accuracies:
                avg_level_acc = sum(level_accuracies) / len(level_accuracies)
                print(f"    {level}: Average accuracy {avg_level_acc:.2%} ({len(level_accuracies)} models)")
    print()
    
    
    # 5.4 Generate deep analysis report
    print("Step 5.5: Generating deep analysis report...")
    analysis_report = generate_analysis_report(summary, benchmark, output_dir)
    print()
    
    # ========== Phase 6: Summary and Recommendations ==========
    print("【Phase 6】Summary and Recommendations")
    print("-" * 80)
    
    print("Evaluation Summary:")
    print(f"  - Evaluated {summary['models_count']} models")
    print(f"  - {summary['total_questions']} questions total")
    if scored_results:
        print(f"  - Best model accuracy: {best_model['accuracy']:.2%}")
        print(f"  - Accuracy gap between models: {(best_model['accuracy'] - worst_model['accuracy']):.2%}")
    else:
        print("  - Accuracy and model comparison: N/A")
    print()
    
    print("Key Recommendations:")
    for i, rec in enumerate(analysis_report["recommendations"], 1):
        print(f"  {i}. {rec}")
    print()
    
    # ========== Output File List ==========
    print("=" * 80)
    print("Generated File List")
    print("=" * 80)
    print(f"\nOutput directory: {output_dir}")
    print("\nFile list:")
    
    file_count = 0
    total_size = 0
    for file in sorted(output_dir.glob("*")):
        if file.is_file():
            size = file.stat().st_size
            total_size += size
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.1f} MB"
            print(f"  - {file.name} ({size_str})")
            file_count += 1
    
    print(f"\nTotal: {file_count} files, total size: {total_size / (1024 * 1024):.2f} MB")
    print("\n" + "=" * 80)
    print("✓ Complete workflow execution completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
