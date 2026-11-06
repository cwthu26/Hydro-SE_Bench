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

**Question sources and expert oversight.** Hydro-SE Bench combines expert-designed questions with LLM-assisted question generation from reference materials, including textbooks, reference books, monographs, Chinese national and industry standards, and laws and regulations. The development team included 35 Hydro-SE domain experts responsible for source selection, question design, answer verification, subfield and task annotation, and quality review. Each candidate question was independently reviewed by at least three experts in addition to its original designer. Review covered technical correctness, the clarity of the answer key, consistency of the explanation with its source, and the assigned subfield and task. Disputed questions were revised and reviewed again; remaining disagreements were discussed to reach consensus, and questions without consensus were excluded.

**Evaluation and human review.** Scoring uses the final selected options. Although the evaluation prompts request reasoning, an accuracy score does not establish that every step of the generated reasoning is correct. As described in the revised evaluation protocol, responses for which the parser found no valid option letter underwent manual review. An unambiguous final selection was recorded when present. Responses with no model output were labelled `failed`; outputs truncated before a final selection were left blank; complete responses rejecting all offered options were labelled `no correct answer`; and responses requesting more information or stating that the answer could not be determined were labelled `I don't know`. After review, responses without an identifiable valid option letter counted as incorrect. The released answer workbook contains the final selections after this process.

**Scope of use.** The primary results describe performance on Chinese-language, closed-ended Hydro-SE questions, including questions grounded in Chinese standards and engineering practice. The English comparison covers DeepSeek-V4-Flash and GPT-5.4 on the same 4,000 items; it does not extend the full 37-model ranking to English. Benchmark accuracy should not be treated as evidence that a model can independently make safe engineering decisions. Applications involving engineering safety require professional assessment and independent verification.

## Commercial API use and funding

**Question generation.** DeepSeek-R1 was accessed through its official API to generate candidate questions. Requests included a source passage, the question-generation instructions, and expert-designed examples. The resulting candidates were subject to the expert review described above. This generation stage is separate from the zero-shot model evaluation.

**Main model evaluation.** All 37 models received Chinese questions and prompts: 22 were accessed through official APIs and 15 through OpenRouter. The `model_status` sheet in the [model answer workbook](reference_results/hydrobench_final_model_answer_table.xlsx) records each model's access channel and access date; the registry in [script 01](code/01hydrobench_model_test.py) records its API model identifier. The revised protocol used a common user-prompt template, no additional system prompt or few-shot examples, temperature 0, a maximum output length of 8,192 tokens, and a 300-second API timeout. Top-p remained at the provider default. Reasoning or thinking mode was enabled where supported, with effort or thinking budget left at the respective API default. Evaluation requests supplied the question and its options without the reference answer. The English comparison used English versions of both the questions and evaluation prompts.

**Confidence elicitation (Fig. 6).** This experiment used Chinese questions and prompts and asked each model for a 0–100% probability that its previously selected answer was completely correct. Requests included the question and that model's prior answer, but withheld the reference answer. The collection routes and API identifiers were:

| Model | Access route | API model identifier |
|---|---|---|
| DeepSeek-V4-Flash | OpenRouter | `deepseek/deepseek-v4-flash` |
| Qwen3.6-Plus | OpenRouter | `qwen/qwen3.6-plus` |
| Kimi K2-0905 | OpenRouter | `moonshotai/kimi-k2-0905` |
| Llama 3.2 3B Instruct | OpenRouter | `meta-llama/llama-3.2-3b-instruct` |
| GPT-5.6-Sol | AIPRO | `gpt-5.6-sol` |
| GLM-4-32B | Hugging Face router | `zai-org/GLM-4-32B-0414:featherless-ai` |

These routes describe the confidence experiment separately from the main evaluation. The [code guide](code/README.md#04--confidence-calibration) provides the collection and analysis commands and links to the archived probability data.

**Cost responsibility.** API usage and routing-service charges incurred in the study, including question generation, model evaluation, and confidence elicitation, were covered by the research group's funds.

## 📝 License

The software is distributed under the [MIT License](LICENSE). The JSON benchmark files include a canary requesting that benchmark questions be kept out of training corpora.
