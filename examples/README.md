# HydroSEBench Evaluation Library Examples

This directory contains complete examples of using the HydroSEBench evaluation library, demonstrating various features of the library.

The bundled `test.csv` contains 4,000 questions with recorded predictions from **DeepSeek-V3.2-Exp** and **Qwen-Plus**. Its columns are `ID,Level,Type,Question,Answer,DeepSeek-V3.2-Exp,Qwen-Plus`. Running the examples scores these recorded predictions without calling model APIs.

**Code demonstration only:** This test file deliberately includes missing standard answers and missing model answers. It differs from the complete official dataset and must not be used to report official benchmark results. The official Chinese and English dataset files retain all standard answers.

The following cells are intentionally empty:

| Column | Number of empty cells | Question IDs |
|---|---:|---|
| `Answer` | 5 | `HWR-47`, `HRD-483`, `ESM-297`, `ESM-109`, `HRD-220` |
| `DeepSeek-V3.2-Exp` | 5 | `HWR-51`, `HRD-493`, `ESM-304`, `ESM-115`, `HRD-229` |
| `Qwen-Plus` | 5 | `HRD-303`, `HSE-187`, `ESM-252`, `GE-221`, `HSE-325` |

The model-answer cells were randomly selected with seed `20261016`. The selected questions do not overlap with the missing-standard questions, each other, or the explicit conclusions described below. Each model therefore has 10 `Unscored` questions: five missing standard answers and five missing model answers.

Qwen-Plus has seven recorded conclusions meaning "no correct option" or "no correct answer": `BK-153`, `BK-191`, `IS-46`, `GE-95`, `ESM-419`, `PS-223`, and `PS-479`. These are explicit model conclusions. They disagree with the valid standard option answers and are scored `Incorrect`. They remain visible in the normal reports and do not appear in the unscored-issue list.

Examples 1, 2, 3, and 5 load both the questions/standard answers and model predictions from `test.csv`, retaining all rows so these exceptional cases appear in the reports. Examples 0 and 4 continue to use the complete official benchmark for data export and sampling.

Questions with missing standard answers, missing model answers, or unusable answers remain in the reports as `Unscored`, with separate reasons. Excel reports include an `Issues` sheet; batch evaluation also writes `score_report_issues.csv` for each model. See [scoring and issue reporting](../hydrosebench-eval/README.md#scoring-and-issue-reporting) for the scoring rules.

Expected results when scoring all 4,000 demonstration rows:

| Model | Correct | Incorrect | Scored | Unscored | Accuracy |
|---|---:|---:|---:|---:|---:|
| DeepSeek-V3.2-Exp | 3,174 | 816 | 3,990 | 10 | 79.55% |
| Qwen-Plus | 2,973 | 1,017 | 3,990 | 10 | 74.51% |

Accuracy is correct answers divided by scored questions. The unscored questions are excluded from this denominator and from the incorrect count.

## Directory Structure

```
examples/
├── example_0_download_data.py      # Download data files
├── example_1_basic_evaluation.py   # Basic single model evaluation
├── example_2_batch_evaluation.py   # Batch evaluate multiple models
├── example_3_custom_benchmark.py   # Use custom benchmark
├── example_4_sampling.py           # Sample questions by category
├── example_5_complete_workflow.py  # Complete workflow example
├── utils.py                        # Common utility functions
├── test.csv                        # Test data file (model predictions)
├── output/                         # Output directory (generated files)
│   ├── example_0_download_data/
│   ├── example_1_basic_evaluation/
│   ├── example_2_batch_evaluation/
│   ├── example_3_custom_benchmark/
│   ├── example_4_sampling/
│   └── example_5_complete_workflow/
└── README.md                       # This file
```

## Example List

### Example 0: Download HydroSEBench Data Files (`example_0_download_data.py`)

Demonstrates how to download the complete Chinese and English datasets using the HydroSEBench library. Each edition includes 4,000 questions and standard answers from the installed package.

**Main Features:**
- Download data files using Python API
- Select Chinese (`zh`, default) or English (`en`)
- Download data files in JSON and CSV formats (package uses CSV format for version control)
- Download to current directory or specified path
- Display command-line download examples that you can run separately
- Verify downloaded files

**How to Run:**
```bash
cd examples
python example_0_download_data.py
```

**Output:**
Files are saved to `examples/output/example_0_download_data/`:
- `hydrosebench.json`
- `hydrosebench.csv`
- `hydrosebench_en.json`
- `hydrosebench_en.csv`
- `my_custom_hydrosebench.csv` (custom filename example)

The current-directory examples also save Chinese JSON and CSV in the directory where the script is run.

**Code Examples:**

Download using Python API:
```python
from hydrosebench import download_hydrosebench_data
from pathlib import Path

# Download JSON file to current directory
json_path = download_hydrosebench_data("json")

# Download CSV file to current directory
csv_path = download_hydrosebench_data("csv")

# Download to specified path
download_hydrosebench_data("json", Path("./data/hydrosebench.json"))
download_hydrosebench_data("csv", Path("./data/hydrosebench.csv"))

# Download English files; default filenames include _en
download_hydrosebench_data("json", language="en")
download_hydrosebench_data("csv", language="en")
```

Download using command-line tools:
```bash
# Download JSON and CSV files to current directory
python -m hydrosebench download

# Download CSV file only
python -m hydrosebench download --format csv

# Download JSON file only
python -m hydrosebench download --format json

# Download to specified directory
python -m hydrosebench download --output ./my_data

# Download English JSON and CSV to the same directory
python -m hydrosebench download --language en --output ./my_data
```

### Example 1: Basic Evaluation Functionality (`example_1_basic_evaluation.py`)

Demonstrates how to use the HydroSEBench library to evaluate a single model.

**Main Features:**
- Load the example benchmark from `test.csv`, including intentionally missing standard answers
- Load model predictions from CSV or Excel file
- Calculate scores and generate reports
- Export reports in JSON, CSV, and Excel formats

**How to Run:**
```bash
cd examples
python example_1_basic_evaluation.py
```

**Input:**
- Uses `examples/test.csv` (or `test.xlsx`) for model predictions

**Output:**
Files are saved to `examples/output/example_1_basic_evaluation/`:
- `basic_evaluation_report.json`
- `basic_evaluation_report.csv`
- `basic_evaluation_report.xlsx`

### Example 2: Batch Evaluate Multiple Models (`example_2_batch_evaluation.py`)

Demonstrates how to batch evaluate multiple models in a CSV or Excel file.

**Main Features:**
- Automatically identify all model columns in the file
- Batch evaluate all models
- Generate detailed reports for each model (JSON and Excel)
- Generate model comparison summary Excel

**How to Run:**
```bash
cd examples
python example_2_batch_evaluation.py
```

**Input:**
- Uses `examples/test.csv` (or `test.xlsx`) with multiple model prediction columns

**Output:**
Files are saved to `examples/output/example_2_batch_evaluation/`:
- `all_models_summary.json` - Summary of all models
- `models_comparison.xlsx` - Comparison table
- `<model_name>/` directories containing:
  - `score_report.csv`
  - `score_report.json`
  - `score_report.xlsx`
  - `score_report_issues.csv`

### Example 3: Using Custom Benchmark (`example_3_custom_benchmark.py`)

Demonstrates how to load a custom benchmark from a CSV or Excel file and perform evaluation.

**Main Features:**
- Load custom benchmark from CSV or Excel file
- Evaluate using custom benchmark
- Display statistics by category and difficulty
- Generate detailed reports

**How to Run:**
```bash
cd examples
python example_3_custom_benchmark.py
```

**Output:**
Files are saved to `examples/output/example_3_custom_benchmark/`:
- `custom_benchmark_report.csv`
- `custom_benchmark_report.json`
- `custom_benchmark_report.xlsx`

### Example 4: Sampling Functionality (`example_4_sampling.py`)

Demonstrates how to sample questions by category from a benchmark.

**Main Features:**
- Sample questions by category
- Create sampled benchmark
- Save sampling results in CSV or JSON format
- Automatically match output format to input format

**How to Run:**
```bash
cd examples
python example_4_sampling.py
```

**Output:**
Files are saved to `examples/output/example_4_sampling/`:
- `sampled_benchmark_from_csv.csv`
- `sampled_benchmark_from_json.json`

### Example 5: Complete Workflow (`example_5_complete_workflow.py`)

Demonstrates the complete workflow from loading data to generating comprehensive reports.

**Main Features:**
- Preview file structure
- Identify model columns
- Batch evaluation of multiple models
- Generate summary reports
- Detailed result analysis
- Export comprehensive reports (including Markdown and Word documents)

**How to Run:**
```bash
cd examples
python example_5_complete_workflow.py
```

**Output:**
Files are saved to `examples/output/example_5_complete_workflow/`:
- `all_models_summary.json`
- `models_comparison.xlsx`
- `detailed_analysis_report.md`
- `detailed_analysis_report.json`
- `detailed_analysis_report.docx` (if supported)
- `detailed_analysis_report.pdf` (if the PDF dependencies are installed)
- `<model_name>/` directories containing detailed reports

## Utility Functions (`utils.py`)

All examples use common utility functions from `utils.py`:

- `setup_package_path()` - Sets up the package path and returns project root
- `get_output_dir(project_root, example_name)` - Gets the output directory for an example
- `get_test_data_path(project_root)` - Gets the test data file path (prioritizes CSV)
- `get_benchmark_data_path(project_root)` - Gets the benchmark data file path (prioritizes CSV)

These functions ensure consistent path handling across all examples.

## Dependencies

Running these examples requires the following dependencies:

```bash
pip install "pandas>=2.0" "openpyxl>=3.0"
```

The package should be installed first:
```bash
cd hydrosebench-eval
pip install -e .
```

`pandas` and `openpyxl` are required package dependencies. Example 5 can additionally generate Word reports with `python-docx`, and PDF reports with `markdown`, `weasyprint`, and the required system libraries. If an optional report dependency is unavailable, that format is skipped and the other reports are still generated.

## Data File Requirements

Most examples require the following data files:

1. **Official Benchmark File (Examples 0 and 4)**: `hydrosebench-eval/hydrosebench/data/hydrosebench.csv` (or `.json`)
   - Contains questions, options, correct answers, etc.
   - CSV format is preferred (lighter weight, suitable for version control)
   - Optional columns: `Level` (difficulty), `Type` (question type)
   - The package includes built-in benchmark, so this file is already available

2. **Example Benchmark and Model Predictions (Examples 1, 2, 3, and 5)**: `examples/test.csv` (or `test.xlsx`)
   - Contains questions, five intentionally missing standard answers, and five intentionally missing answers in each model column
   - Requires `ID` column for matching questions
   - One column per model, with model name as column header
   - Bundled models: "DeepSeek-V3.2-Exp" and "Qwen-Plus"

## Output File Description

After running examples, files are generated in the `examples/output/<example_name>/` directory:

1. **Individual Model Reports** (`<model_name>/score_report.xlsx`, `.json`, `.csv`)
   - Each model has its own folder containing reports in multiple formats
   - Contains detailed comparison of question content, correct answers, and model answers
   - Excel includes statistics tables by category, difficulty, and question type; CSV contains per-question details
   - CSV format is recommended for version control

2. **Model Comparison Summary** (`models_comparison.xlsx`)
   - Score comparison of all models
   - Model comparisons by category, difficulty, and question type

3. **Summary Data** (`all_models_summary.json`)
   - Complete evaluation data, including statistics by category and difficulty
   - JSON format, convenient for program processing

4. **Unscored Issues** (`<model_name>/score_report_issues.csv`, Examples 2 and 5)
   - Lists only questions that could not be scored and their reasons
   - Explicit conclusions that disagree with valid standard answers are included in the normal reports as `Incorrect`

5. **Other Reports**
   - Example 5 generates additional reports in Markdown and Word formats
   - Sampling examples generate sampled benchmark files

## Notes

1. **Running from project root**: All examples can be run from the project root:
   ```bash
   python examples/example_1_basic_evaluation.py
   ```

2. **Output directory**: Reports are saved to `examples/output/<example_name>/` automatically. Example 0 also demonstrates exporting Chinese data files to the current working directory.

3. **File formats**: The examples prioritize CSV format for data files (lighter weight, better for version control)

4. **Data file paths**: The `utils.py` helper functions automatically handle file path resolution, prioritizing CSV over Excel when both exist

5. **Modifying examples**: You can modify the examples to use your own data files by changing the paths in the code

6. **Disk space**: Ensure sufficient disk space to save output files, especially for batch evaluation with many models

## More Information

For more information about the HydroSEBench evaluation library, please refer to:
- Main README: `../README.md` - Dataset overview and introduction
- Package README: `../hydrosebench-eval/README.md` - Complete API documentation and usage guide
