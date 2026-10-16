"""
Example 4: Sampling Functionality
Demonstrates how to sample questions by category from a benchmark
"""

from utils import setup_package_path, get_output_dir, get_benchmark_data_path

# Setup package path
PROJECT_ROOT = setup_package_path()

from hydrosebench import (
    load_builtin_benchmark,
    load_benchmark_from_file,
    sample_benchmark_by_category,
    sample_examples_by_category,
    save_benchmark,
)


def main():
    """Sampling functionality example"""
    print("=" * 80)
    print("Example 4: Sampling Functionality")
    print("=" * 80)
    print()
    
    # 1. Load benchmark
    print("Step 1: Loading benchmark...")
    benchmark = load_builtin_benchmark("hydrosebench")
    print(f"✓ Benchmark loaded, {len(benchmark.examples)} questions total")
    print()
    
    # 2. Sample questions by category
    print("Step 2: Sampling questions by category...")
    print("Sampling 5 questions from each category...")
    
    sampled_examples = sample_examples_by_category(
        benchmark,
        per_category=5
    )
    
    print(f"✓ Sampling completed, {len(sampled_examples)} questions sampled")
    print()
    
    # Display sampling result statistics
    from collections import Counter
    categories = []
    for example in sampled_examples:
        category = example.category
        if category:
            categories.append(category)
    
    category_counts = Counter(categories)
    print("Sampling results by category distribution:")
    print("-" * 80)
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count} questions")
    print()
    
    # 3. Create sampled benchmark and auto-save
    print("Step 3: Creating sampled benchmark...")
    output_dir = get_output_dir(PROJECT_ROOT, "example_4_sampling")
    
    # Automatically select output format based on input format
    # Since we're using built-in benchmark (loaded from JSON), output JSON
    output_file = output_dir / "sampled_benchmark_from_json.json"
    
    sampled_benchmark = sample_benchmark_by_category(
        benchmark,
        per_category=5,
        output_path=output_file  # Auto-save, format automatically detected based on input
    )
    
    print(f"✓ Sampled benchmark created, {len(sampled_benchmark.examples)} questions total")
    print(f"✓ Sampling results auto-saved: {output_file}")
    print()
    
    # 4. Demonstrate loading from csv and sampling (if csv file exists)
    excel_benchmark_path = get_benchmark_data_path(PROJECT_ROOT)
    if excel_benchmark_path.exists():
        print("Step 4: Demonstrating loading from csv/excel and sampling...")
        excel_benchmark = load_benchmark_from_file(excel_benchmark_path)
        
        # Loaded from csv, output csv format
        excel_output_file = output_dir / "sampled_benchmark_from_csv.csv"
        sampled_excel_benchmark = sample_benchmark_by_category(
            excel_benchmark,
            per_category=5,
            output_path=excel_output_file  # Auto-save as csv format
        )
        
        print(f"✓ Loading from Excel and sampling completed, {len(sampled_excel_benchmark.examples)} questions total")
        print(f"✓ Sampling results auto-saved as csv: {excel_output_file}")
        print()
    
    print("\n" + "=" * 80)
    print("Example completed!")
    print("=" * 80)
    print(f"\nOutput files saved to: {output_dir}")
    print("Note: Output format is automatically selected based on input format (JSON input -> JSON output, csv input -> csv output)")


if __name__ == "__main__":
    main()
