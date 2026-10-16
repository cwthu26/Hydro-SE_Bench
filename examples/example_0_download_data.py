"""
Example 0: Download HydroSEBench Data Files
Demonstrates how to use the HydroSEBench library to download built-in hydrosebench.json and hydrosebench.csv files

This example demonstrates two methods:
1. Download using Python API
2. Download using command-line tools

Note: Package data files use CSV format (lighter weight, suitable for version control),
     If Excel format is needed, it can be converted from CSV or use report export functionality.
"""

from pathlib import Path
from utils import setup_package_path, get_output_dir

# Setup package path
PROJECT_ROOT = setup_package_path()

from hydrosebench import download_hydrosebench_data


def download_with_python_api():
    """Download data files using Python API"""
    print("=" * 80)
    print("Method 1: Download using Python API")
    print("=" * 80)
    print()
    
    output_dir = get_output_dir(PROJECT_ROOT, "example_0_download_data")
    
    # Example 1: Download JSON file to current directory
    print("Example 1.1: Download JSON file to current directory")
    print("-" * 80)
    json_path = download_hydrosebench_data("json")
    print(f"✓ JSON file downloaded to: {json_path}")
    print(f"  File size: {json_path.stat().st_size / 1024:.2f} KB")
    print()
    
    # Example 2: Download CSV file to current directory
    print("Example 1.2: Download CSV file to current directory")
    print("-" * 80)
    csv_path = download_hydrosebench_data("csv")
    print(f"✓ CSV file downloaded to: {csv_path}")
    print(f"  File size: {csv_path.stat().st_size / 1024:.2f} KB")
    print()
    
    # Example 3: Download JSON file to specified directory
    print("Example 1.3: Download JSON file to specified directory")
    print("-" * 80)
    custom_json_path = output_dir / "hydrosebench.json"
    json_path = download_hydrosebench_data("json", custom_json_path)
    print(f"✓ JSON file downloaded to: {json_path}")
    print()
    
    # Example 4: Download CSV file to specified directory
    print("Example 1.4: Download CSV file to specified directory")
    print("-" * 80)
    custom_csv_path = output_dir / "hydrosebench.csv"
    csv_path = download_hydrosebench_data("csv", custom_csv_path)
    print(f"✓ CSV file downloaded to: {csv_path}")
    print()
    
    # Example 5: Download to custom filename
    print("Example 1.5: Download to custom filename")
    print("-" * 80)
    custom_path = output_dir / "my_custom_hydrosebench.csv"
    csv_path = download_hydrosebench_data("csv", custom_path)
    print(f"✓ CSV file downloaded to: {csv_path}")
    print()
    
    return output_dir


def download_with_cli():
    """Download data files using command-line tools"""
    print("=" * 80)
    print("Method 2: Download using command-line tools")
    print("=" * 80)
    print()
    
    print("The following commands can be run in the terminal:")
    print()
    
    print("1. Download all formats (JSON, CSV) to current directory:")
    print("   python -m hydrosebench download")
    print()
    
    print("2. Download only JSON file:")
    print("   python -m hydrosebench download --format json")
    print()
    
    print("3. Download only CSV file (recommended, lightweight):")
    print("   python -m hydrosebench download --format csv")
    print()
    
    print("4. Download to specified directory:")
    print("   python -m hydrosebench download --output ./my_data")
    print()
    
    print("5. Download to specified file path:")
    print("   python -m hydrosebench download --format csv --output ./my_data/hydrosebench.csv")
    print()
    
    print("Note: Command-line method requires installing the hydrosebench package first")
    print("     Installation: pip install -e ../hydrosebench-eval")
    print()


def verify_downloaded_files(output_dir: Path):
    """Verify downloaded files"""
    print("=" * 80)
    print("Verify Downloaded Files")
    print("=" * 80)
    print()
    
    json_file = output_dir / "hydrosebench.json"
    csv_file = output_dir / "hydrosebench.csv"
    
    if json_file.exists():
        print(f"✓ JSON file exists: {json_file}")
        print(f"  File size: {json_file.stat().st_size / 1024:.2f} KB")
        
        # Try reading JSON file to verify format
        import json
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    print(f"  Contains {len(data)} records")
                elif isinstance(data, dict) and 'examples' in data:
                    print(f"  Contains {len(data['examples'])} records")
        except Exception as e:
            print(f"  ⚠️  Error reading JSON file: {e}")
    else:
        print(f"✗ JSON file does not exist: {json_file}")
    
    print()
    
    if csv_file.exists():
        print(f"✓ CSV file exists: {csv_file}")
        print(f"  File size: {csv_file.stat().st_size / 1024:.2f} KB")
        
        # Try reading CSV file to verify format
        try:
            import pandas as pd
            df = pd.read_csv(csv_file, nrows=0, encoding='utf-8')  # Only read column names
            print(f"  Contains columns: {', '.join(df.columns.tolist())}")
        except Exception as e:
            print(f"  ⚠️  Error reading CSV file: {e}")
    else:
        print(f"✗ CSV file does not exist: {csv_file}")
    
    print()


def main():
    """Main function"""
    print()
    print("=" * 80)
    print("Example 0: Download HydroSEBench Data Files")
    print("=" * 80)
    print()
    print("This example demonstrates how to download built-in hydrosebench.json and hydrosebench.csv files")
    print("These files contain complete benchmark dataset data and can be used for local evaluation and analysis")
    print()
    print("Note: CSV format is lighter weight and suitable for version control. If Excel format is needed,")
    print("     you can use report export functionality (report.to_excel()) or convert from CSV.")
    print()
    
    # Download using Python API
    output_dir = download_with_python_api()
    
    # Show command-line method
    download_with_cli()
    
    # Verify downloaded files
    verify_downloaded_files(output_dir)
    
    print("=" * 80)
    print("Example completed!")
    print("=" * 80)
    print()
    print(f"All files saved to: {output_dir}")
    print()


if __name__ == "__main__":
    main()
