"""
Example 3: Using Custom Benchmark
Demonstrates how to load a custom benchmark from CSV or Excel file and perform evaluation
"""

from utils import setup_package_path, get_output_dir, get_test_data_path

# Setup package path
PROJECT_ROOT = setup_package_path()

from hydrosebench import (
    load_benchmark_from_file,
    load_predictions_from_excel,
    Benchmark,
)


def main():
    """Custom benchmark example"""
    print("=" * 80)
    print("Example 3: Using Custom Benchmark")
    print("=" * 80)
    print()
    
    # 1. Load custom benchmark from CSV or Excel file
    print("Step 1: Loading custom benchmark...")
    benchmark_excel = get_test_data_path(PROJECT_ROOT)
    
    if not benchmark_excel.exists():
        print(f"⚠ Example file does not exist: {benchmark_excel}")
        print("Please ensure benchmark CSV or Excel file exists")
        return
    
    # Try reading file to check columns first (optional, for display purposes)
    # If it fails, just load the benchmark directly
    import pandas as pd
    file_ext = benchmark_excel.suffix.lower()
    has_level_col = None
    has_type_col = None
    
    try:
        if file_ext == ".csv":
            # Try reading first few rows to check columns (using same logic as package)
            # Using simple approach here, skip check if it fails
            try:
                df_check = pd.read_csv(benchmark_excel, nrows=5, engine='python', encoding='utf-8')
            except:
                try:
                    df_check = pd.read_csv(benchmark_excel, nrows=5, engine='python', encoding='gbk')
                except:
                    df_check = None
            file_type = "CSV"
        else:
            df_check = pd.read_excel(benchmark_excel, nrows=5)
            file_type = "Excel"
        
        if df_check is not None:
            print(f"{file_type} file columns: {list(df_check.columns)}")
            has_level_col = "Level" in df_check.columns
            has_type_col = "Type" in df_check.columns
            print(f"  - Has 'Level' column: {has_level_col}")
            print(f"  - Has 'Type' column: {has_type_col}")
            
            if has_level_col:
                print(f"  - First few 'Level' values: {df_check['Level'].head(3).tolist()}")
            if has_type_col:
                print(f"  - First few 'Type' values: {df_check['Type'].head(3).tolist()}")
    except Exception as e:
        print(f"⚠ Unable to read file for column check (will load benchmark directly): {e}")
    
    # Load benchmark using package function (it automatically handles CSV reading compatibility issues)
    # Explicitly specify column names to ensure correct reading of Level and Type
    benchmark = load_benchmark_from_file(
        benchmark_excel,
        level_col="Level" if has_level_col else None,  # Difficulty column name (if detected)
        type_col="Type" if has_type_col else None,     # Question type column name (if detected)
        category_col="ID",   # Category column name (extracted from ID)
    )
    print(f"✓ Custom benchmark loaded, {len(benchmark.examples)} questions total")
    
    # Check if difficulty and question type information exists
    examples_with_level = sum(1 for ex in benchmark.examples if ex.level)
    examples_with_type = sum(1 for ex in benchmark.examples if ex.question_type)
    examples_with_category = sum(1 for ex in benchmark.examples if ex.category)
    print(f"  - Questions with difficulty info: {examples_with_level}/{len(benchmark.examples)}")
    print(f"  - Questions with question type info: {examples_with_type}/{len(benchmark.examples)}")
    print(f"  - Questions with category info: {examples_with_category}/{len(benchmark.examples)}")
    
    # Display some example level and type values
    if examples_with_level > 0:
        sample_levels = [ex.level for ex in benchmark.examples[:5] if ex.level]
        print(f"  - Example Level values: {sample_levels[:3]}")
    if examples_with_type > 0:
        sample_types = [ex.question_type for ex in benchmark.examples[:5] if ex.question_type]
        print(f"  - Example Type values: {sample_types[:3]}")
    
    if examples_with_level == 0:
        print(f"  ⚠ Warning: {file_type} file may not have 'Level' column, or column name doesn't match")
        if not has_level_col:
            print(f"     Hint: {file_type} file indeed doesn't have 'Level' column")
            print("     Solution: If column name is different (e.g., 'Difficulty'), modify level_col parameter")
    if examples_with_type == 0:
        print(f"  ⚠ Warning: {file_type} file may not have 'Type' column, or column name doesn't match")
        if not has_type_col:
            print(f"     Hint: {file_type} file indeed doesn't have 'Type' column")
            print("     Solution: If column name is different (e.g., 'Question Type'), modify type_col parameter")
    print()
    
    # 2. Load model predictions
    print("Step 2: Loading model predictions...")
    predictions_excel = get_test_data_path(PROJECT_ROOT)
    
    if not predictions_excel.exists():
        print(f"⚠ Example file does not exist: {predictions_excel}")
        print("Please ensure predictions CSV or Excel file exists")
        return
    
    predictions = load_predictions_from_excel(
        predictions_excel,
        id_col="ID",
        answer_col="DeepSeek-V3.2-Exp"  # Please modify according to actual column name
    )
    
    # Keep missing or unusable answers so scoring can report each issue
    print(f"✓ Loaded {len(predictions)} predictions")
    print()
    
    # 3. Calculate scores
    print("Step 3: Calculating scores...")
    report = benchmark.score(predictions)
    
    # 4. Display results
    print("\n" + "=" * 80)
    print("Evaluation Results")
    print("=" * 80)
    print(report.summary())
    print()
    
    # 5. Display statistics by category
    category_stats = report.get_category_stats(benchmark)
    if category_stats:
        print("\nStatistics by Category:")
        print("-" * 80)
        for category, stats in sorted(category_stats.items()):
            accuracy = "N/A" if stats["accuracy"] is None else f"{stats['accuracy']:.2%}"
            print(f"{category}: {stats['correct']}/{stats['scored']} ({accuracy}), unscored={stats['unscored']}")
    
    # 6. Display statistics by difficulty
    level_stats = report.get_level_stats(benchmark)
    if level_stats:
        print("\nStatistics by Difficulty:")
        print("-" * 80)
        for level, stats in sorted(level_stats.items()):
            accuracy = "N/A" if stats["accuracy"] is None else f"{stats['accuracy']:.2%}"
            print(f"{level}: {stats['correct']}/{stats['scored']} ({accuracy}), unscored={stats['unscored']}")
    
    # 7. Save reports (optional)
    output_dir = get_output_dir(PROJECT_ROOT, "example_3_custom_benchmark")
    
    # Save JSON report
    json_file = output_dir / "custom_benchmark_report.json"
    json_file.write_text(report.to_json(), encoding="utf-8")
    print(f"\n✓ JSON report saved: {json_file}")
    
    # Save CSV report (lightweight, recommended)
    try:
        csv_file = output_dir / "custom_benchmark_report.csv"
        report.to_csv(csv_file, benchmark=benchmark)
        print(f"✓ CSV report saved: {csv_file}")
    except ImportError:
        print("⚠ pandas not installed, skipping CSV report generation")
    
    # Save Excel report (if pandas and openpyxl are installed)
    try:
        excel_file = output_dir / "custom_benchmark_report.xlsx"
        report.to_excel(excel_file, benchmark=benchmark)
        print(f"✓ Excel report saved: {excel_file}")
    except ImportError:
        print("⚠ pandas or openpyxl not installed, skipping Excel report generation")
    
    print("\n" + "=" * 80)
    print("Example completed!")
    print("=" * 80)
    print(f"\nOutput files saved to: {output_dir}")


if __name__ == "__main__":
    main()

