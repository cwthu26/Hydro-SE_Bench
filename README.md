# HydroSEBench Dataset

HydroSEBench is a professional evaluation dataset specifically designed for the water conservancy and hydropower field, aimed at comprehensively assessing models' capabilities in water engineering expertise, engineering applications, and reasoning calculations.

## 📊 Dataset Overview

The HydroSEBench dataset contains **4,000** questions covering nine core professional directions in water conservancy and hydropower. Chinese and English editions are available for evaluating professional capabilities in the water engineering domain.

> **Complete dataset**: All 4,000 questions and standard answers are included in both Chinese and English, in JSON and CSV formats.

![Question Distribution](Question_Distribution.png)

### Overall Statistics

- **Total Questions**: 4,000
- **Single-Choice Questions**: 2,696 (67.4%)
- **Multiple-Choice Questions**: 1,304 (32.6%)

### Difficulty Distribution

The dataset is divided into three difficulty levels, balancing fundamental knowledge and advanced reasoning capabilities:

- **Basic Conceptual Knowledge**: 1,650 questions (41.25%)
- **Engineering Applications**: 1,650 questions (41.25%)
- **Reasoning and Calculation**: 700 questions (17.5%)

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

## ✨ Dataset Features

1. **Comprehensive Coverage**: Covers core knowledge domains in water conservancy and hydropower engineering, from basic concepts to engineering practice
2. **Difficulty Levels**: Balances fundamental knowledge and advanced reasoning to comprehensively assess model capabilities
3. **Diverse Question Types**: Includes both single-choice and multiple-choice questions, closer to real-world application scenarios
4. **Bilingual Editions**: Chinese and English editions cover water engineering domain knowledge
5. **Professional Quality**: Questions are reviewed by water engineering experts through multiple rounds, ensuring professionalism and accuracy

## 📥 Getting the Dataset

Dataset files are located in the `hydrosebench-eval/hydrosebench/data/` directory, available in the following formats:

| Language | JSON | CSV | Built-in benchmark |
|---|---|---|---|
| Chinese | [hydrosebench.json](hydrosebench-eval/hydrosebench/data/hydrosebench.json) | [hydrosebench.csv](hydrosebench-eval/hydrosebench/data/hydrosebench.csv) | `hydrosebench` |
| English | [hydrosebench_en.json](hydrosebench-eval/hydrosebench/data/hydrosebench_en.json) | [hydrosebench_en.csv](hydrosebench-eval/hydrosebench/data/hydrosebench_en.csv) | `hydrosebench_en` |

Each edition contains 4,000 records. JSON retains the existing benchmark metadata and `examples` schema (`input`, `target_scores`, `ID`, `category`, `level`, `type`). CSV uses the existing columns `ID,Level,Type,Question,Answer`, encoded as UTF-8 with BOM; category is the ID prefix.

```python
from hydrosebench import load_builtin_benchmark
benchmark = load_builtin_benchmark("hydrosebench_en")
```

```bash
hydrosebench evaluate --benchmark hydrosebench_en --predictions predictions.json
```

The Python package includes both complete editions. Select `zh` (Chinese, default) or `en` (English) when downloading:

```bash
python -m hydrosebench download --language zh --output ./data
python -m hydrosebench download --language en --output ./data
```

Each command exports JSON and CSV. Chinese filenames are `hydrosebench.json` and `hydrosebench.csv`; English filenames are `hydrosebench_en.json` and `hydrosebench_en.csv`, so both editions can share a directory. These commands copy data bundled with the installed package; update your package installation to obtain newer data.

For detailed download and installation instructions, see: 📖 **[Installation Guide](INSTALL.md#download-dataset-files)**

## 🔧 Using the Evaluation Tools

We provide a dedicated Python package for evaluating model performance on the HydroSEBench dataset. The evaluation tools support:

- ✅ Batch evaluation of multiple models
- ✅ Automatic generation of detailed evaluation reports (Excel, JSON, Markdown)
- ✅ Statistical analysis by category, difficulty, and question type
- ✅ Support for custom benchmarks
- ✅ Flexible answer format support

### Quick Start with Evaluation Tools

For detailed installation and usage instructions, see:

- 📖 **[Complete Evaluation Tool Documentation](hydrosebench-eval/README.md)** - Complete API documentation, usage examples, and command-line tool instructions
- 🔧 **[Installation Instructions](hydrosebench-eval/README.md#installation)** - Package installation steps
- 🚀 **[Quick Start](hydrosebench-eval/README.md#quick-start)** - Quick start example code

## 📁 Project Structure

```
Hydro-SE-Bench/
├── hydrosebench-eval/          # HydroSEBench evaluation toolkit
│   ├── hydrosebench/           # Core modules
│   │   └── data/             # Built-in dataset
│   │       ├── hydrosebench.json
│   │       ├── hydrosebench.csv
│   │       ├── hydrosebench_en.json
│   │       └── hydrosebench_en.csv
│   └── README.md             # Complete evaluation tool documentation
├── examples/                  # Usage example code
│   ├── example_0_download_data.py
│   ├── example_1_basic_evaluation.py
│   └── ...
└── README.md                 # This file (dataset introduction)
```

## 📚 Additional Resources

- **Evaluation Tool Documentation**: [hydrosebench-eval/README.md](hydrosebench-eval/README.md) - Complete API documentation and usage guide for evaluation tools
- **Example Code**: [examples/](examples/) - Detailed usage examples and code demonstrations
- **Example Documentation**: [examples/README.md](examples/README.md) - Detailed explanation of all examples

## 📄 Data Format

The CSV fields are listed below. JSON stores question text as `input`, answers as `target_scores` (1 = correct, 0 = incorrect), and category/level/type as lowercase fields:

- **ID**: Unique question identifier (e.g., "BK-1", "HWR-1")
- **Question**: Question content (including options)
- **Answer**: Correct answer (e.g., "C" or "A,B")
- **Category** (JSON `category`, derived from ID in CSV): Category code (BK, IS, HWR, GE, HSE, ESM, HRD, M, PS)
- **Level**: Difficulty level (Basic Conceptual Knowledge, Engineering Applications, Reasoning and Calculation)
- **Type**: Question type (Single-choice, Multiple-choice)

For detailed format specifications, see [Evaluation Tool Documentation](hydrosebench-eval/README.md#file-format-requirements).

## Feedback

For questions about the dataset or evaluation tools, please [open an issue](https://github.com/cwthu26/Hydro-SE-Bench/issues).

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

**HydroSEBench** - Professional Evaluation Dataset for Water Conservancy and Hydropower Domain

## Scoring and issue reporting

Scoring continues when a question has a missing/invalid standard answer or a missing/unparseable model response. These questions are retained as `Unscored`, with their IDs, original responses and reasons, and are excluded from both the incorrect count and the accuracy denominator. Accuracy is correct / scored questions; reports also show total and unscored counts. When no question is scorable, accuracy is unavailable (`null` in JSON, `N/A` in text).

Normal reports include issue annotations. The CLI also writes a separate `*_issues.csv`, and Excel includes an `Issues` worksheet. Batch evaluation retains empty or failed-response model columns and includes their issue details in the final results. Question-level issues do not cause a nonzero exit code; processing failures such as unreadable files or duplicate IDs remain errors. See the [evaluation documentation](hydrosebench-eval/README.md#scoring-and-issue-reporting) for details.
