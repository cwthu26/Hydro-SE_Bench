# Installation and Usage Guide

## Installation Steps

### 1. Install Python Package

Install or upgrade from PyPI with Python 3.10 or later:

```bash
python -m pip install --upgrade hydrosebench
```

Alternatively, download the repository, navigate to the `hydrosebench-eval` directory and install:

```bash
cd hydrosebench-eval
pip install -e .
```

Or install directly (without entering the directory):

```bash
pip install -e hydrosebench-eval
```

To upgrade an existing installation from the current repository, run this from the repository root:

```bash
python -m pip install --upgrade ./hydrosebench-eval
```

Version `0.1.2` includes both complete language editions and the updated scoring rules. Updating a repository does not automatically update an installed package or a package-index release.

### 2. Verify Installation

Run the following command to verify the installation was successful:

```python
python -c "from hydrosebench import load_builtin_benchmark; print('Installation successful!')"
```

## Download Dataset Files

Dataset files are located in the `hydrosebench-eval/hydrosebench/data/` directory, available in the following formats:

- **Chinese**: [hydrosebench.json](hydrosebench-eval/hydrosebench/data/hydrosebench.json) and [hydrosebench.csv](hydrosebench-eval/hydrosebench/data/hydrosebench.csv)
- **English**: [hydrosebench_en.json](hydrosebench-eval/hydrosebench/data/hydrosebench_en.json) and [hydrosebench_en.csv](hydrosebench-eval/hydrosebench/data/hydrosebench_en.csv)

Each edition contains 4,000 questions and standard answers. Both editions are bundled with the package. Use `language="zh"` (default) for Chinese or `language="en"` for English. Downloading copies the files from the installed package and does not fetch updates from the internet.

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

# Download English files (use language="zh" for Chinese)
download_hydrosebench_data("json", language="en")
download_hydrosebench_data("csv", Path("./data/hydrosebench_en.csv"), language="en")
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

# Download English JSON and CSV to the same directory
python -m hydrosebench download --language en --output ./data

# Download English CSV only
python -m hydrosebench download --language en --format csv --output ./data

# Download specified format to specified path
python -m hydrosebench download --format csv --output ./my_data/hydrosebench.csv
```

`--language zh` selects Chinese explicitly. With default filenames, Chinese uses `hydrosebench.json` / `hydrosebench.csv`, and English uses `hydrosebench_en.json` / `hydrosebench_en.csv`. Both languages can be saved together without overwriting each other. An explicit output filename is used as supplied.

### Method 3: Direct File Access

Dataset files can also be accessed directly from the `hydrosebench-eval/hydrosebench/data/` directory without downloading.

### Run Download Example

You can run the example code to see how the download feature works:

```bash
cd examples
python example_0_download_data.py
```

## Running Examples

The example scripts and `test.csv` are provided in the repository, separately from the installed package. Download the repository before running the commands below.

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
