# Installation and Usage Guide

## Installation Steps

### 1. Install Python Package

Navigate to the `hydrosebench-eval` directory and install:

```bash
cd hydrosebench-eval
pip install -e .
```

Or install directly (without entering the directory):

```bash
pip install -e hydrosebench-eval
```

### 2. Verify Installation

Run the following command to verify the installation was successful:

```python
python -c "from hydrosebench import load_builtin_benchmark; print('Installation successful!')"
```

## Download Dataset Files

Dataset files are located in the `hydrosebench-eval/hydrosebench/data/` directory, available in the following formats:

- **Chinese**: [hydrosebench.json](hydrosebench-eval/hydrosebench/data/hydrosebench.json) and [hydrosebench.csv](hydrosebench-eval/hydrosebench/data/hydrosebench.csv)
- **English**: [hydrosebench_en.json](hydrosebench-eval/hydrosebench/data/hydrosebench_en.json) and [hydrosebench_en.csv](hydrosebench-eval/hydrosebench/data/hydrosebench_en.csv)

Each edition contains 4,000 questions and standard answers. The download API and command below export the Chinese edition; use the links above for the English files.

### Method 1: Download Using Python API

If the `hydrosebench` Python package is installed, you can download using the following code:

```python
from hydrosebench import download_hydrosebench_data
from pathlib import Path

# Download JSON file to current directory
json_path = download_hydrosebench_data("json")
print(f"JSON file downloaded to: {json_path}")

# Download CSV file to specified directory
csv_path = download_hydrosebench_data("csv", Path("./data/hydrosebench.csv"))
print(f"CSV file downloaded to: {csv_path}")
```

### Method 2: Download Using Command Line

```bash
# Download all formats to current directory
python -m hydrosebench download

# Download only JSON file
python -m hydrosebench download --format json

# Download only CSV file (recommended, lighter weight)
python -m hydrosebench download --format csv

# Download to specified directory
python -m hydrosebench download --output ./data

# Download specified format to specified path
python -m hydrosebench download --format csv --output ./my_data/hydrosebench.csv
```

### Method 3: Direct File Access

Dataset files can also be accessed directly from the `hydrosebench-eval/hydrosebench/data/` directory without downloading.

### Run Download Example

You can run the example code to see how the download feature works:

```bash
cd examples
python example_0_download_data.py
```

## Running Examples

### Method 1: Run Example Files Directly

```bash
cd examples
python example_1_basic_evaluation.py
```

### Method 2: Run from the Repository Root

```bash
python examples/example_1_basic_evaluation.py
```

## Dependency Installation

If you encounter import errors, install the following dependencies:

```bash
pip install "pandas>=2.0" "openpyxl>=3.0"
```

## Common Issues

### Issue 1: Cannot find hydrosebench module

**Solution**: Ensure the package is installed, or check Python path settings.

### Issue 2: Cannot find data files

**Solution**: Data files are located in the `hydrosebench-eval/hydrosebench/data/` directory. Ensure this directory exists.

### Issue 3: Excel file read error

**Solution**: Ensure the `openpyxl` library is installed:
```bash
pip install openpyxl
```

## Next Steps

- Check `examples/README.md` for all examples
- Check `hydrosebench-eval/README.md` for complete API documentation
