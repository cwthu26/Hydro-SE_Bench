# HydroSEBench Evaluation Library Examples

This directory contains complete examples of using the HydroSEBench evaluation library, demonstrating various features of the library.

The bundled `test.csv` contains 4,000 questions with recorded predictions from **DeepSeek-V3.2-Exp** and **Qwen-Plus**. Its columns are `ID,Level,Type,Question,Answer,DeepSeek-V3.2-Exp,Qwen-Plus`. Running the examples scores these recorded predictions without calling model APIs.

**Code demonstration only:** This test file includes exceptional cases such as missing standard answers and model responses that cannot be scored. Five randomly selected `Answer` cells have intentionally been cleared: `HWR-47`, `HRD-483`, `ESM-297`, `ESM-109`, and `HRD-220`. Qwen-Plus also has seven recorded responses such as `无正确选项` (no correct option) or `无正确答案` (no correct answer). These are model responses, not verified defects in the benchmark. Consequently, `test.csv` is not identical to the official benchmark described in the main README, and its results are provided only to demonstrate the code, not as official benchmark results. The official dataset files are unchanged.

Examples 1, 2, 3, and 5 load both the questions/standard answers and model predictions from `test.csv`, retaining all rows so these exceptional cases appear in the reports. Examples 0 and 4 continue to use the complete official benchmark for data export and sampling.

**中文说明：** `test.csv` 专门考虑了标准答案缺失、模型无法给出可评分答案等异常情况，其中随机清空了 5 道题的参考答案，并保留模型“无正确选项／无正确答案”等原始回答。因此，该测试文件与正文介绍的正式数据不完全一致，仅作为代码测试示例提供，不应用于报告正式评测成绩。正式题库文件未作修改。

Questions with missing standard answers, missing model answers, or unusable answers remain in the reports as `Unscored`, with separate reasons. Excel reports include an `Issues` sheet; batch evaluation also writes `score_report_issues.csv` for each model. See [scoring and issue reporting](../hydrosebench-eval/README.md#scoring-and-issue-reporting) for the scoring rules.

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

Demonstrates how to download the built-in `hydrosebench.json` and `hydrosebench.csv` files using the HydroSEBench library.

**Main Features:**
- Download data files using Python API
- Download data files in JSON and CSV formats (package uses CSV format for version control)
- Download to current directory or specified path
- Download data files using command-line tools
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
```

### Example 1: Basic Evaluation Functionality (`example_1_basic_evaluation.py`)

Demonstrates how to use the HydroSEBench library to evaluate a single model.

**Main Features:**
- Load the example benchmark from `test.csv`, including intentionally missing standard answers
- Load model predictions from CSV or Excel file
- Calculate scores and generate reports
- Export reports in JSON and Excel formats

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
pip install pandas openpyxl
```

The package should be installed first:
```bash
cd hydrosebench-eval
pip install -e .
```

If you only need basic functionality (without Excel reports), you can skip `openpyxl`.

## Data File Requirements

Most examples require the following data files:

1. **Official Benchmark File (Examples 0 and 4)**: `hydrosebench-eval/hydrosebench/data/hydrosebench.csv` (or `.json`)
   - Contains questions, options, correct answers, etc.
   - CSV format is preferred (lighter weight, suitable for version control)
   - Optional columns: `Level` (difficulty), `Type` (question type)
   - The package includes built-in benchmark, so this file is already available

2. **Example Benchmark and Model Predictions (Examples 1, 2, 3, and 5)**: `examples/test.csv` (or `test.xlsx`)
   - Contains questions, standard answers (including five intentionally empty cells), and model prediction results
   - Requires `ID` column for matching questions
   - One column per model, with model name as column header
   - Bundled models: "DeepSeek-V3.2-Exp" and "Qwen-Plus"

## Output File Description

After running examples, files are generated in the `examples/output/<example_name>/` directory:

1. **Individual Model Reports** (`<model_name>/score_report.xlsx`, `.json`, `.csv`)
   - Each model has its own folder containing reports in multiple formats
   - Contains detailed comparison of question content, correct answers, and model answers
   - Contains statistics tables by category and difficulty
   - CSV format is recommended for version control

2. **Model Comparison Summary** (`models_comparison.xlsx`)
   - Score comparison of all models
   - Model comparisons by category, difficulty, and question type

3. **Summary Data** (`all_models_summary.json`)
   - Complete evaluation data, including statistics by category and difficulty
   - JSON format, convenient for program processing

4. **Other Reports**
   - Example 5 generates additional reports in Markdown and Word formats
   - Sampling examples generate sampled benchmark files

## Notes

1. **Running from project root**: All examples can be run from the project root:
   ```bash
   python examples/example_1_basic_evaluation.py
   ```

2. **Output directory**: All outputs are saved to `examples/output/<example_name>/` automatically

3. **File formats**: The examples prioritize CSV format for data files (lighter weight, better for version control)

4. **Data file paths**: The `utils.py` helper functions automatically handle file path resolution, prioritizing CSV over Excel when both exist

5. **Modifying examples**: You can modify the examples to use your own data files by changing the paths in the code

6. **Disk space**: Ensure sufficient disk space to save output files, especially for batch evaluation with many models

## More Information

For more information about the HydroSEBench evaluation library, please refer to:
- Main README: `../README.md` - Dataset overview and introduction
- Package README: `../hydrosebench-eval/README.md` - Complete API documentation and usage guide
