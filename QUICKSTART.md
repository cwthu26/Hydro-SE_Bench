# Quick Start Guide

## 5-Minute Quick Start

### Step 1: Install Package

```bash
cd hydrosebench-eval
pip install -e .
```

### Step 2: Run First Example

```bash
cd ../examples
python example_1_basic_evaluation.py
```

## Core Features Demonstration

### Feature 1: Batch Evaluate Multiple Models

```python
from hydrosebench import evaluate_all_models, create_summary_excel, load_benchmark_from_file
from pathlib import Path

# Run from the repository root; use the demonstration's standard answers.
benchmark = load_benchmark_from_file("examples/test.csv")
summary = evaluate_all_models(
    "examples/test.csv",
    benchmark=benchmark,
    output_dir="./results"
)

# Generate summary report
create_summary_excel(summary, Path("./results"), benchmark)
```

The demonstration includes five missing standard answers and model responses that cannot be scored. It differs from the complete official dataset and is provided only to exercise the code; see [the example documentation](examples/README.md).

### Feature 2: View Evaluation Results

```python
# View rankings of all models
for idx, result in enumerate(summary["results"], 1):
    accuracy = "N/A" if result["accuracy"] is None else f"{result['accuracy']:.2%}"
    print(f"{idx}. {result['model_name']}: {accuracy}; unscored={result['unscored_count']}")
```

## Example Files Description

| Example File | Description |
|--------------|-------------|
| `example_0_download_data.py` | Download benchmark dataset |
| `example_1_basic_evaluation.py` | Basic evaluation functionality |
| `example_2_batch_evaluation.py` | Batch evaluate multiple models |
| `example_3_custom_benchmark.py` | Use custom benchmark |
| `example_4_sampling.py` | Sampling functionality |
| `example_5_complete_workflow.py` | Complete workflow |

## Output Files

After running batch evaluation, the following will be generated:

1. **Model Detailed Reports**: `<model_name>/score_report.xlsx` and `<model_name>/score_report.json`
2. **Model Comparison Summary**: `models_comparison.xlsx`
3. **Summary Data**: `all_models_summary.json`
4. **Separate Issue Details**: `<model_name>/score_report_issues.csv`; Excel reports also include an `Issues` worksheet

## Need Help?

- Check `README.md` for complete documentation
- Check `INSTALL.md` for installation issues
- Check `examples/README.md` for all examples
