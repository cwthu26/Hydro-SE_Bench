# HydroSEBench

`HydroSEBench` provides a lightweight Python package for calculating model scores based on the HydroSEBench evaluation dataset.

## Core Features

- **Built-in Dataset**: Complete Chinese and English editions, each with 4,000 questions and answers in JSON and CSV
- **Data File Download**: Support downloading package data files via code or command line (JSON, CSV)
- **Multiple Format Support**: Support JSON, CSV, and Excel formats for benchmarks and prediction results
- **Batch Evaluation**: Support evaluating answers from multiple models at once
- **Flexible Answer Formats**: Support single-choice and multiple-choice questions; compatible with strings, lists, dictionaries, and other input formats

## Dataset Statistics

The HydroSEBench dataset contains **4,000** questions covering nine core professional directions in water conservancy and hydropower, comprehensively assessing models' capabilities in water engineering expertise, engineering applications, and reasoning calculations.

### Overall Overview

- **Total Questions**: 4,000
- **Single-Choice Questions**: 2,696 (67.4%)
- **Multiple-Choice Questions**: 1,304 (32.6%)

### Difficulty Distribution

The dataset is divided into three difficulty levels, balancing fundamental knowledge and advanced reasoning capabilities:

- **Basic Conceptual Knowledge**: 1,650 questions (41.25%)
- **Engineering Applications**: 1,650 questions (41.25%)
- **Reasoning and Calculation**: 700 questions (17.5%)

> Note: The total number of questions across all difficulty levels is 4,000. The percentages above are rounded approximations.

### Category Distribution

The dataset covers the following nine professional directions, each containing a different number of questions:

| Category Code | Category Name | Total | Single-Choice | Multiple-Choice | Basic Conceptual Knowledge | Engineering Applications | Reasoning and Calculation |
|---------------|---------------|-------|---------------|-----------------|---------------------------|--------------------------|---------------------------|
| **BK** | Background Knowledge | 250 | 217 | 33 | 250 | 0 | 0 |
| **IS** | Industry Standard | 250 | 160 | 90 | 0 | 250 | 0 |
| **HWR** | Hydrology and Water Resources | 500 | 311 | 189 | 200 | 200 | 100 |
| **GE** | Geotechnical Engineering | 500 | 297 | 203 | 200 | 200 | 100 |
| **HSE** | Hydraulic Structures and Equipment | 500 | 336 | 164 | 200 | 200 | 100 |
| **ESM** | Engineering Safety and Management | 500 | 318 | 182 | 200 | 200 | 100 |
| **HRD** | Hydraulics and River Dynamic | 500 | 358 | 142 | 200 | 200 | 100 |
| **M** | Meteorology | 500 | 336 | 164 | 200 | 200 | 100 |
| **PS** | Power System | 500 | 363 | 137 | 200 | 200 | 100 |

### Dataset Features

1. **Comprehensive Coverage**: Covers core knowledge domains in water conservancy and hydropower engineering, from basic concepts to engineering practice
2. **Difficulty Levels**: Balances fundamental knowledge and advanced reasoning to comprehensively assess model capabilities
3. **Diverse Question Types**: Includes both single-choice and multiple-choice questions, closer to real-world application scenarios
4. **Bilingual Editions**: Chinese and English questions cover the same water engineering categories

## Installation

Run in the `hydrosebench-eval` directory:

```bash
pip install -e .
```

## Quick Start

### 1. Download Data Files (Optional)

If you need to obtain the package data files:

```python
from hydrosebench import download_hydrosebench_data
from pathlib import Path

# Download to current directory
download_hydrosebench_data("json")
download_hydrosebench_data("csv")

# Download to specified path
download_hydrosebench_data("json", Path("./data/hydrosebench.json"))
download_hydrosebench_data("csv", Path("./data/hydrosebench.csv"))
```

Or use command line:

```bash
python -m hydrosebench download                    # Download all formats to current directory
python -m hydrosebench download --format csv     # Download CSV only
python -m hydrosebench download --format json    # Download JSON only
python -m hydrosebench download --output ./data   # Download to specified directory
```

### 2. Evaluate Using Built-in Benchmark

```python
from hydrosebench import Benchmark, load_builtin_benchmark

# Select three questions for this small example.
source = load_builtin_benchmark("hydrosebench")  # "hydrosebench_en" for English
benchmark = Benchmark(name="demo", description=None, examples=source.examples[:3])

# Prepare model predictions (dictionary format: {question_id: answer})
predictions = {
    "BK-1": "C",
    "BK-2": "A,B",
    "BK-3": ["B"],
}

# Calculate scores
report = benchmark.score(predictions)
print(report.summary())
print(f"Unscored questions: {report.unscored_count}")
```

For a full evaluation, score `source` directly. Any question without a usable standard answer or model answer is retained and marked `Unscored`; evaluation continues.

### 3. Load Predictions from CSV or Excel Files

```python
from hydrosebench import load_builtin_benchmark, load_predictions_from_excel

benchmark = load_builtin_benchmark("hydrosebench")

# Load model predictions from CSV or Excel
predictions = load_predictions_from_excel(
    "model_output.csv",  # or "model_output.xlsx"
    id_col="ID",         # Question ID column name
    answer_col="Answer"  # Answer column name
)

report = benchmark.score(predictions)
print(report.summary())
```

### 4. Batch Evaluate Multiple Models

If the CSV or Excel file contains answer columns from multiple models:

```python
from hydrosebench import evaluate_all_models

# Automatically identify all model columns and batch evaluate
summary = evaluate_all_models(
    "model_output.csv",  # or "model_output.xlsx"
    benchmark_name="hydrosebench",
    output_dir="./results"
)

# View results
for result in summary["results"]:
    accuracy = "N/A" if result["accuracy"] is None else f"{result['accuracy']:.2%}"
    print(f"{result['model_name']}: {accuracy}; unscored={result['unscored_count']}")
```

## Command Line Usage

### Single Model Evaluation

```bash
# Using JSON format prediction results
python -m hydrosebench evaluate \
  --benchmark hydrosebench \
  --predictions model_output.json

# Using CSV or Excel format prediction results
python -m hydrosebench evaluate \
  --benchmark hydrosebench \
  --predictions model_output.csv \
  --predictions-id-col "ID" \
  --predictions-answer-col "Answer" \
  --output report.csv  # Auto-detect format, supports .json, .csv, .xlsx, .md
```

### Batch Evaluate Multiple Models

```bash
python -m hydrosebench batch-evaluate \
  --excel model_output.csv \
  --benchmark hydrosebench \
  --output-dir ./results
```

These commands use the complete built-in benchmark. The bundled `examples/test.csv` is a code demonstration with five deliberately missing standard answers and recorded model responses that cannot be scored. To exercise those cases, run the scripts in [examples](../examples/README.md), which load their standard answers from that test file. Demonstration scores are not official benchmark results.

### Using Custom Benchmarks

```bash
# Load benchmark from CSV or Excel file
python -m hydrosebench evaluate \
  --benchmark-excel custom_benchmark.csv \
  --predictions model_output.csv \
  --predictions-id-col "ID" \
  --predictions-answer-col "Answer"

# Load benchmark from JSON file
python -m hydrosebench evaluate \
  --benchmark-path custom_benchmark.json \
  --predictions model_output.json
```

## File Format Requirements

### Benchmark CSV/Excel (Standard Answer File)

- **Required Column**: `Question` (question content)
- **Standard Answers**: `Answer` (e.g., "C" or "A,B"); a missing column or blank cell is reported as a missing standard answer
- **Optional Columns**: `ID` (question ID), `Level` (difficulty level), `Type` (question type)
- **Recommended Format**: CSV (lighter weight, suitable for version control)

### Predictions CSV/Excel (Model Prediction File)

- **Required Column**: Answer column (default `Answer`, can be specified via parameter)
- **Recommended Column**: `ID` (matches ID in benchmark)
- **Matching Method**: Match by ID if `ID` column exists, otherwise match by row order
- **Answer Format**: Supports `"C"` (single-choice), `"A,B"` (multiple-choice), etc.
- **Recommended Format**: CSV (lighter weight, suitable for version control)

### JSON Prediction File Format

Supports the following three formats:

```json
// Format 1: List (by question order)
["C", "A,B", "B"]

// Format 2: Dictionary (keys are question IDs)
{
  "BK-1": "C",
  "BK-2": "A,B",
  "BK-3": "B"
}

// Format 3: List of objects
[
  {"id": "BK-1", "answer": "C"},
  {"id": "BK-2", "answer": ["A", "B"]}
]
```

## Additional Features

### Random Sampling

```python
from hydrosebench import load_builtin_benchmark, sample_benchmark_by_category

benchmark = load_builtin_benchmark("hydrosebench")

# Randomly sample the same number of questions from each category
sampled = sample_benchmark_by_category(
    benchmark,
    per_category=5,
    seed=42
)
```

### Export Detailed Reports

Supports multiple formats for easy viewing and sharing:

```python
report = benchmark.score(predictions)

# Export as CSV (lightweight, recommended for version control)
report.to_csv("report.csv", benchmark=benchmark)
report.to_issues_csv("report_issues.csv")  # Separate list of unscored questions

# Export as Excel (most intuitive, suitable for viewing)
report.to_excel("report.xlsx", benchmark=benchmark)

# Export as Markdown table
report.to_markdown("report.md", benchmark=benchmark)

# Export as JSON (for program processing)
with open("report.json", "w", encoding="utf-8") as f:
    f.write(report.to_json())

# View in console
for score in report.example_scores:
    print(f"{score.status} {score.example_id}: Expected {score.expected}, Predicted {score.predicted}; {score.reason}")
```

**CSV/Excel reports include**:
- Question ID, question content, category, difficulty, question type
- Correct answer vs model answer comparison
- Correct/Incorrect/Unscored status, original model response, issue codes and explanations
- Summary statistics

**CSV Format Advantages**:
- Smaller files, faster loading
- Suitable for version control and Git diff
- Can be opened with any text editor

**Excel Format Advantages**:
- Multiple worksheet support (detailed results, statistics by category, statistics by difficulty, etc.)
- Better formatting and column width settings
- Suitable for direct viewing and sharing

**Markdown Reports**: Suitable for display in documentation or sharing

---

For detailed API documentation, see the code documentation.

## Full bilingual dataset and validation

Use `load_builtin_benchmark("hydrosebench")` for Chinese or `load_builtin_benchmark("hydrosebench_en")` for English. Each edition contains 4,000 source records in bundled JSON and CSV. See the [dataset README](../README.md) for file links.

### Scoring and issue reporting

Evaluation continues when an individual question cannot be scored. Normal questions are marked `Correct` or `Incorrect`; affected questions are marked `Unscored` with one or more reasons:

| Issue code | Meaning |
|---|---|
| `missing_standard_answer` | No standard answer was supplied |
| `invalid_standard_answer` | The standard answer refers to an option absent from the question |
| `missing_model_answer` | A prediction is absent or empty, including null/NaN values |
| `unparseable_model_answer` | The response does not contain a supported, definite answer |
| `invalid_model_answer` | The parsed answer refers to an option absent from the question |

`No answer`, `Timeout`, `I do not know`, and `无法作答` are retained as unscored responses. Accepted answer forms include `A`, `a`, `A,B`, uppercase compact choices such as `AB`, lists such as `["A", "B"]`, and wrappers using `answer`, `answers`, `choices`, `prediction`, or `output`. Short explicit forms such as `The answer is A.` and `答案：A` are also accepted. Arbitrary prose and ambiguous alternatives are not guessed.

**Accuracy = correct questions / scored questions.** Unscored questions are excluded from both the incorrect count and the accuracy denominator. For example, 6 correct, 2 incorrect and 2 unscored questions produce 75% accuracy on 8 scored questions, with 10 total questions. Always compare coverage alongside accuracy. If no question can be scored, accuracy is `None` in Python, `null` in JSON and `N/A` in text reports.

`report.max_score` is the scored count; `report.total_questions` is the full count. Reports expose `unscored_count`, `issue_counts` and `issues`. A question can have multiple reasons, so reason counts may sum to more than the number of unscored questions. Its `is_correct` value is `None`, not `False`. Category, difficulty and question-type statistics follow the same denominator and include `total`, `scored` and `unscored` counts.

### Output files

- JSON retains every question, its original response, status and reasons, plus an `issues` list and summary counts.
- CSV and Excel add `Status`, `Raw Model Answer`, `Issue Codes` and `Issue Details`. Excel also contains a separate `Issues` worksheet.
- Markdown includes the status and reason beside each question.
- Single-model CLI evaluation with `--output report.json` (or `.csv`, `.xlsx`, `.md`) also writes `report_issues.csv` beside the normal report. The issues file contains only a header when no issues exist.
- Batch evaluation writes normal JSON/CSV/Excel reports and `score_report_issues.csv` for every model. `all_models_summary.json` includes each model's unscored counts and issue details, including models with no scorable responses.

Batch evaluation treats every column other than recognized metadata and the selected ID column as a model column, including empty columns and columns containing only failed responses. Keep unrelated auxiliary columns out of the prediction table. Recognized metadata includes question, standard answer, category, level, type and token-count columns.

Question-level issues do not stop evaluation or cause a nonzero CLI exit code. File-reading failures, invalid file structure or duplicate IDs that prevent unambiguous matching remain processing errors. Batch processing records these in `errors`, continues with other models and returns a nonzero CLI exit code if a processing error occurred.
