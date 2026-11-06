# Hydro-SE Bench

Hydro-SE Bench evaluates large language models on closed-book questions in hydroscience and engineering.

- **Chinese edition.** The benchmark was developed in Chinese using sources such as hydroscience and engineering textbooks and industry standards. It combines expert-written questions with model-generated questions reviewed by experts. All 37 models in the main evaluation received Chinese questions and prompts.
- **English edition.** The authors translated the finalized Chinese questions into English. DeepSeek-V4-Flash and GPT-5.4 answered the same 4,000 items with English questions and prompts for comparison with their Chinese results.

## 📊 Dataset Overview

Both editions share the same **4,000 questions** and reference answers. Of these, **2,702** are single-choice (67.55%) and **1,298** are multiple-choice (32.45%).

Across nine domains, each question assesses one of three tasks.

- **Task A · Basic conceptual knowledge** — 1,650 questions (41.25%)
- **Task B · Engineering applications** — 1,650 questions (41.25%)
- **Task C · Reasoning and calculation** — 700 questions (17.50%)

![Question distribution by domain, task and question type](question%20distribution.png)

*Panel a shows the distribution across domains. Panels b and c show the number of options per single-choice and multiple-choice question.*

### Category Distribution

| Domain | Total | Single-choice | Multiple-choice | Task A | Task B | Task C |
|---|---:|---:|---:|---:|---:|---:|
| Background Knowledge (BK) | 250 | 217 | 33 | 250 | 0 | 0 |
| Industry Standards (IS) | 250 | 160 | 90 | 0 | 250 | 0 |
| Hydrology and Water Resources (HWR) | 500 | 311 | 189 | 200 | 200 | 100 |
| Geotechnical Engineering (GE) | 500 | 298 | 202 | 200 | 200 | 100 |
| Hydraulic Structures and Equipment (HSE) | 500 | 336 | 164 | 200 | 200 | 100 |
| Engineering Safety and Management (ESM) | 500 | 324 | 176 | 200 | 200 | 100 |
| Hydraulics and River Dynamics (HRD) | 500 | 358 | 142 | 200 | 200 | 100 |
| Meteorology (M) | 500 | 335 | 165 | 200 | 200 | 100 |
| Power Systems (PS) | 500 | 363 | 137 | 200 | 200 | 100 |
| **All domains** | **4,000** | **2,702** | **1,298** | **1,650** | **1,650** | **700** |

## 📥 Getting the Dataset

Each file contains one complete language edition, including the questions, options and reference answers.

| Language | JSON | CSV |
|---|---|---|
| Chinese | [hydrosebench.json](data/hydrosebench.json) | [hydrosebench.csv](data/hydrosebench.csv) |
| English | [hydrosebench_en.json](data/hydrosebench_en.json) | [hydrosebench_en.csv](data/hydrosebench_en.csv) |

The [question authorship annotations](data/hydrobench_question_authorship.json) group the IDs into 1,502 human-authored questions and 2,498 model-generated, expert-reviewed questions.

## 🔧 Using the Evaluation Scripts

Install the dependencies and run the commands from the repository root with Python 3.10 or later. For example, the following command recomputes the overall accuracy and 95% bootstrap interval for each model from its archived Chinese answers.

```sh
python -m pip install -r requirements.txt
python code/02bootstrap_overall_accuracy.py --input reference_results/hydrobench_final_model_answer_table.xlsx --output results/Overall_accuracy_bootstrap.csv
```

The [archived overall accuracy table](reference_results/Overall_accuracy_bootstrap.csv) contains the corresponding results for all 37 models. The [code guide](code/README.md) gives commands for new model evaluations, paired comparisons, calibration and subsampling.

## 📁 Project Structure

```text
.
├── .github/workflows/    GitHub Actions configuration for the offline tests
├── data/                 Chinese and English benchmark files and authorship annotations
├── code/                 Five evaluation and analysis scripts and their usage guide
├── reference_results/    Model answer and probability workbooks and two bootstrap tables
├── tests/                24 offline software tests and their reader guide
├── .gitignore
├── question distribution.png
├── requirements.txt
├── LICENSE
└── README.md
```

Use the [model answer workbook](reference_results/hydrobench_final_model_answer_table.xlsx) for final answers and the [probability workbook](reference_results/calibration_model_probabilities.xlsx) for the six-model calibration analysis. Join question records by ID.

The [test guide](tests/README.md) describes each of the 24 offline checks. The [GitHub Actions workflow](.github/workflows/tests.yml) runs them on pushes and pull requests and also supports manual runs.

## 📄 Data Format

The JSON files store questions in the top-level `examples` list. The CSV files use UTF-8 with BOM. Each CSV row contains one question, including its option lines.

| Meaning | JSON field | CSV field |
|---|---|---|
| Question ID | `ID` | `ID`, e.g. `BK-1` |
| Domain | `category` | Prefix of `ID`, e.g. `BK` |
| Competency task | `task` | `Task`, e.g. `basic conceptual knowledge` |
| Question type | `type` | `Type`, either `single choice` or `multiple choice` |
| Stem and options | `input` | `Question`, with options on separate lines |
| Reference answer | `target_scores`, with 1 for each correct option and 0 for each incorrect option | `Answer`, with letters written together (e.g. `C` or `ABC`) |

For example, `BK-1` has the JSON answer key `{"A": 0, "B": 0, "C": 1, "D": 0}` and the CSV answer `C` in both editions. Mathematical expressions are part of the question text. The notation includes `_(...)` for a subscript, `^(...)` for an exponent, `√(...)` for a square root and `root[3](...)` for a cube root.

## Ethics and responsible use

Model-generated candidate questions underwent expert review for technical correctness and answer validity before inclusion. This human oversight supports the quality of the benchmark; it does not establish that evaluated models can independently make safe engineering decisions. Applications involving engineering safety require professional assessment and independent verification of model outputs.

## Commercial API use

**Question generation.** DeepSeek-R1 was accessed through its official API. Requests supplied source passages, question-generation instructions, and expert-designed examples.

**Main evaluation.** Of the 37 models, 22 were accessed through official APIs and 15 through OpenRouter. Requests supplied the evaluation prompt, question and options, without the reference answer. Per-model channels and access dates are recorded in the `model_status` sheet of the [answer workbook](reference_results/hydrobench_final_model_answer_table.xlsx); API model identifiers are listed in [script 01](code/01hydrobench_model_test.py).

**Confidence elicitation (Fig. 6).** Requests supplied the question and the model's previously selected answer, asking for its probability of being completely correct. Reference answers were withheld. This experiment used the following routes, which are reported separately from the main evaluation:

| Model | Access route | API model identifier |
|---|---|---|
| DeepSeek-V4-Flash | OpenRouter | `deepseek/deepseek-v4-flash` |
| Qwen3.6-Plus | OpenRouter | `qwen/qwen3.6-plus` |
| Kimi K2-0905 | OpenRouter | `moonshotai/kimi-k2-0905` |
| Llama 3.2 3B Instruct | OpenRouter | `meta-llama/llama-3.2-3b-instruct` |
| GPT-5.6-Sol | AIPRO | `gpt-5.6-sol` |
| GLM-4-32B | Hugging Face router | `zai-org/GLM-4-32B-0414:featherless-ai` |

The [code guide](code/README.md) describes the generation settings and the collection and analysis commands.

## Funding

API usage and routing-service charges for question generation, model evaluation, and confidence elicitation were covered by the research group's funds.

## 📝 License

The software is distributed under the [MIT License](LICENSE). The JSON benchmark files include a canary requesting that benchmark questions be kept out of training corpora.
