"""
Example 2: Batch Evaluate Multiple Models
Demonstrates how to use the HydroSEBench library to batch evaluate multiple models in a CSV or Excel file
"""

from utils import setup_package_path, get_output_dir, get_test_data_path

# Setup package path
PROJECT_ROOT = setup_package_path()

from hydrosebench import evaluate_all_models, load_benchmark_from_file, create_summary_excel


def main():
    """Batch evaluation example"""
    print("=" * 80)
    print("Example 2: Batch Evaluate Multiple Models")
    print("=" * 80)
    print()
    
    # 1. Set input and output paths
    excel_path = get_test_data_path(PROJECT_ROOT)
    output_dir = get_output_dir(PROJECT_ROOT, "example_2_batch_evaluation")
    
    if not excel_path.exists():
        print(f"⚠ Example file does not exist: {excel_path}")
        print("Please ensure test.csv or test.xlsx exists, or modify excel_path to point to your data file")
        return
    
    print(f"Input file: {excel_path}")
    print(f"Output directory: {output_dir}")
    print()
    
    # 2. Use the example's standard answers and retain rows with missing answers
    benchmark = load_benchmark_from_file(excel_path)
    
    # 3. Execute batch evaluation
    # evaluate_all_models will automatically:
    # - Identify all model columns in the Excel file
    # - Calculate scores for each model
    # - Generate detailed Excel reports (one file per model)
    # - Save summary JSON file
    print("Executing batch evaluation...")
    summary = evaluate_all_models(
        excel_path,
        benchmark=benchmark,
        output_dir=output_dir,
        verbose=True,
    )
    
    # 3. Generate model comparison summary Excel
    print("\nGenerating model comparison summary...")
    create_summary_excel(summary, output_dir, benchmark)
    
    # 4. Display summary results
    print("\n" + "=" * 80)
    print("Evaluation completed!")
    print("=" * 80)
    print(f"\nEvaluated {summary['models_count']} models, {summary['total_questions']} questions total")
    print("\nModel score ranking (sorted by accuracy):")
    print("-" * 80)
    print(f"{'Rank':<6} {'Model Name':<40} {'Score':<15} {'Accuracy':<12}")
    print("-" * 80)
    
    for idx, result in enumerate(summary["results"], 1):
        score_str = f"{result['total_score']}/{result['max_score']}"
        accuracy_str = "N/A" if result["accuracy"] is None else f"{result['accuracy']:.2%}"
        rank = idx if result["accuracy"] is not None else "N/A"
        print(f"{rank!s:<6} {result['model_name']:<40} {score_str:<15} {accuracy_str:<12} Unscored: {result['unscored_count']}")
    
    print("\n" + "=" * 80)
    print("Output File Description:")
    print("=" * 80)
    print(f"1. Detailed report for each model: {output_dir}/<model_name>/")
    print("   - score_report.xlsx: Detailed comparison of question content, correct answers, and model answers")
    print("   - score_report.json: Detailed data in JSON format")
    print("   - score_report.csv: Per-question results in CSV format")
    print("   - score_report_issues.csv: Separate list of unscored questions and reasons")
    print("   - Contains statistics tables by category and difficulty")
    print(f"2. Model comparison summary (Excel): {output_dir}/models_comparison.xlsx")
    print("   - Score comparison of all models")
    print("   - Model comparisons by category, difficulty, and question type")
    print(f"3. Summary data (JSON): {output_dir}/all_models_summary.json")
    print("   - Complete evaluation data, including statistics by category and difficulty, convenient for program processing")
    print("=" * 80)


if __name__ == "__main__":
    main()
