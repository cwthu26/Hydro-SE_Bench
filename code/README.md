# Hydro-SE Bench evaluation and analysis scripts

Script 01 collects new answers from a model. To analyze the paper’s archived answers, go directly to scripts 02–05 and use the workbooks in [reference_results/](../reference_results/). Scripts 04 and 05 write the numerical tables underlying Figs. 6 and 7.

Run the examples from the repository root with Python 3.10 or later. Install the analysis dependencies once:

```sh
python -m pip install -r requirements.txt
```

## 01 · Model evaluation and answer extraction

**Paper correspondence.** Section 2.3 and Table 4 describe the evaluation prompt and the rules for extracting answer options. [01hydrobench_model_test.py](01hydrobench_model_test.py) implements that protocol.

**Input and output.** Use the [Chinese](../data/hydrosebench.json) or [English](../data/hydrosebench_en.json) benchmark JSON. A live run writes a JSONL file with one record per attempted question and a manifest of the run settings. The archived final answers are in the [answer workbook](../reference_results/hydrobench_final_model_answer_table.xlsx), in `results` for Chinese and `English_version_results` for English.

**API access for the main evaluation.** Of the 37 models evaluated on the Chinese benchmark, 22 have the access channel `Official API` and 15 have `OpenRouter`. To look up a particular model, see the `API Access Channel` column on the `model_status` sheet of the [answer workbook](../reference_results/hydrobench_final_model_answer_table.xlsx). The model registry in script 01 also lists the API model identifier and access date for each model.

Use these commands to list the registered models and preview a Chinese request for DeepSeek-V4-Flash.

```sh
python code/01hydrobench_model_test.py --list-models
python code/01hydrobench_model_test.py --dataset data/hydrosebench.json --language zh --model-name "DeepSeek-V4-Flash" --api-url https://api.deepseek.com/chat/completions --api-key-env DEEPSEEK_API_KEY --thinking-parameter thinking --thinking enabled --limit 1 --output results/deepseek_answers.jsonl
```

For live collection, set the named environment variable privately and add `--execute`. The example uses `--limit 1` to select one pending question. Omit it to process all pending questions in the input file. Select the matching English file and `--language en` for English evaluation. Defaults are temperature 0, 8,192 maximum output tokens, a 300-second timeout, one worker and up to three HTTP attempts per question. Top-p uses the provider default. Choose the reasoning-mode switch supported by the endpoint. The paper used thinking mode where available and the provider's default effort or token budget.

**Read the first run.** Open the output JSONL. Each line records the result for one question in that round. The `attempts` field counts HTTP attempts within the round. Use `id` to find the question, `model_answer` to read the reply, `extracted_answer` to see the letters the script found, and `finish_reason` to see why the provider stopped generating text. The extractor tries a final-answer line first, followed by an inline final answer, an explicit answer label, a JSON answer field and finally option letters near the end of the reply. A status of `ok` means the script found letters. Correctness is determined later by comparing the final selection with the reference answer.

**Decide which questions need another attempt.**

| What you see in the JSONL | How to interpret it |
|---|---|
| `model_answer` is empty | There is no answer text to review. Check `status` and, for a request failure, `error`. |
| The model wrote an explanation, but `extracted_answer` is empty | The extractor could not identify an option. Read the full reply. Accept letters only if the model clearly gave them as its final selection. |
| `finish_reason` is `length` or `max_tokens` | The reply hit the output limit. For example, it may mention option B while still comparing options. Even if the extractor recorded B and set `status` to `ok`, check whether the model actually finished its answer. |

**Retest unresolved items.** After reviewing the first round, make a copy of the input benchmark JSON containing only the unresolved records in its `examples` list. Keep their original IDs, questions and options. Run 01 on that file with the same model, language, prompt and generation settings. Give each round a new JSONL output path. Resuming the original file skips records already marked `ok`. The paper’s procedure allows up to two further rounds. Review the replies together by question ID and retain one final outcome per question. Leave a question unresolved if the model never gives an unambiguous answer. The archived answer workbook contains the selections after this review.

## 02 · Overall accuracy

**Paper correspondence.** The bootstrap method is described in Section 2.4. Section 3.2 reports the overall results. [02bootstrap_overall_accuracy.py](02bootstrap_overall_accuracy.py) computes the accuracy and interval columns of Table 7 and the individual-model estimates used in Fig. 3c.

**Input and output.** The script reads final predictions and reference answers from the `results` worksheet. The output has one row per model with its rank, correct count, question count, accuracy and 95% interval. Blank or failed predictions count as incorrect. Compare the output with the [archived overall accuracy table](../reference_results/Overall_accuracy_bootstrap.csv).

```sh
python code/02bootstrap_overall_accuracy.py --input reference_results/hydrobench_final_model_answer_table.xlsx --output results/Overall_accuracy_bootstrap.csv
```

**Read the result.** Open `results/Overall_accuracy_bootstrap.csv` and find the row for the model of interest. For example, the archived Qwen3.6-Plus row has 3,286 correct answers out of 4,000, giving 82.15% accuracy. The next two columns give its 95% interval, 81.03% to 83.28%.

To estimate that interval, the script repeatedly samples questions with replacement within each domain, task and question-type group. It uses the same sampled questions for all models. The defaults are 10,000 draws and seed 42.

## 03 · Paired model comparisons

**Paper correspondence.** Section 2.4 describes the paired bootstrap. Section 3.2 and Fig. 3c report comparisons among the eight leading models. [03paired_bootstrap_comparisons.py](03paired_bootstrap_comparisons.py) generates the pairwise statistics reported in Supplementary Table 3.

**Input and output.** The script reads the same `results` worksheet as script 02. Its output has one row per model pair. The interval here describes a *difference between two models*, whereas script 02 reports an interval for each model’s accuracy.

```sh
python code/03paired_bootstrap_comparisons.py --input reference_results/hydrobench_final_model_answer_table.xlsx --output results/Paired_bootstrap_comparisons.csv
```

**Read the result.** Open `results/Paired_bootstrap_comparisons.csv` and find the two models of interest. `Difference (pp)` is the first model’s accuracy minus the second model’s accuracy, in percentage points. For example, Qwen3.6-Plus scored 82.15% and GPT-5.6-Sol scored 82.00%. Their difference is +0.15 points, with a paired 95% interval from −0.98 to +1.25 points. The final column reads `No` because the Holm-adjusted P value exceeds 0.05.

By default the script selects the eight highest-scoring models, compares all 28 pairs on the same sampled questions, and adjusts the two-sided bootstrap P values across those pairs. It uses the same strata, 10,000 draws and seed 42 as script 02. The [archived comparison table](../reference_results/Paired_bootstrap_comparisons.csv) gives all 28 results.

## 04 · Confidence calibration

**Paper correspondence.** Section 2.5 describes confidence elicitation. Section 3.5 and Fig. 6 present the calibration results. [04calibration.py](04calibration.py) has two modes: `collect` asks for the probability that the model’s previous answer is correct, and `analyze` computes the bin counts, mean probabilities and observed accuracies underlying Fig. 6.

**Input and output.** For the paper analysis, use the final answer workbook and the [six-model probability workbook](../reference_results/calibration_model_probabilities.xlsx). The latter has a `probabilities` worksheet and a `response_status` worksheet keyed by question ID. Each invocation analyzes one model and writes three CSV files.

To analyze one of the six archived models for Fig. 6, supply its exact workbook column name.

```sh
python code/04calibration.py analyze --input reference_results/hydrobench_final_model_answer_table.xlsx --model-column "DeepSeek-V4-Flash" --responses reference_results/calibration_model_probabilities.xlsx --output-dir results/calibration/deepseek
```

**Read the result.** Open the files in `results/calibration/deepseek/` according to the question you want to answer.

| File | What to look for |
|---|---|
| `calibration_probability_summary.csv` | Start here for the model’s overall calibration error (ECE), the number of questions included and the counts excluded. Blank or failed original answers and unresolved probability responses are excluded. |
| `calibration_probability_bins.csv` | Use these rows for Fig. 6. Each row groups questions with similar reported confidence. Compare the group’s mean probability with the percentage the model actually answered correctly. For example, the 0–10% bin for DeepSeek-V4-Flash contains 90 questions, with mean confidence 0.65% and observed accuracy 31.111%. |
| `calibration_probability_questions.csv` | Inspect the confidence and outcome for a particular question ID. |

ECE summarizes the gaps shown in the bin table: take the absolute difference between mean confidence and observed accuracy in each nonempty bin, then average those differences in proportion to the number of questions in each bin. The script uses ten bins, includes 100% in the last bin and calculates ECE from bin means rounded to three decimal places.

**Collect new probabilities.** Use `collect` only when the confidence responses you need have yet to be collected. To calculate Fig. 6 from the archived workbooks, the `analyze` command above is sufficient.

The following command previews the collection prompt for a model's previous answer.

```sh
python code/04calibration.py collect --input reference_results/hydrobench_final_model_answer_table.xlsx --model-column "DeepSeek-V4-Flash" --api-model deepseek/deepseek-v4-flash --api-url https://openrouter.ai/api/v1/chat/completions --api-key-env OPENROUTER_API_KEY --limit 1 --output results/deepseek_probabilities.jsonl
```

The Chinese prompt includes the question and the model's selected answer and withholds the reference answer. Collection defaults to temperature 0, a 2,048-token output limit, 120 seconds per request and up to three attempts. Add `--execute` for live collection. For targeted retesting, pass the first JSONL with `--retest-from` and choose a different output file. This raises the default token limit to 8,192 for the selected retest. Use `--retest-invalid` to include invalid probability replies. To analyze multiple rounds, pass first-pass and retest files to `analyze --responses` in that order.

## 05 · Subsampling stability

**Paper correspondence.** Section 4.1 and Fig. 7 examine how accuracy varies with the proportion of questions sampled. [05subsampling.py](05subsampling.py) computes the means and standard deviations for the two models in Fig. 7 and the separate tolerance summaries across all 37 models.

**Input and output.** The script reads the final answers in the `results` worksheet and writes three CSV files. Use `subsampling_accuracy.csv` for the Fig. 7 series and the two tolerance files for the all-model analysis.

```sh
python code/05subsampling.py --input reference_results/hydrobench_final_model_answer_table.xlsx --output-dir results/subsampling
```

**Read the result.** To see how sensitive a model’s accuracy is to the questions sampled, open `results/subsampling/subsampling_accuracy.csv` and follow the same model and task across sample fractions. For example, at 10% the DeepSeek-V3.2-Exp row for Task A summarizes 100 draws of 165 Task A questions each. Its mean accuracy is 81.04%, with a standard deviation of 2.80 percentage points across draws.

Each draw samples without replacement within domain and task. The default seed is 42. At 100%, every question is included, so the script evaluates the full set once and the standard deviation is zero. For the tolerance analysis, a draw passes when its task accuracy lies within five percentage points of that model’s full-task accuracy (the default threshold).

The command above creates `results/subsampling/` locally and writes the three CSV files listed below.

| CSV generated by script 05 | Interpretation |
|---|---|
| `subsampling_accuracy.csv` | Mean accuracy and population standard deviation for DeepSeek-V3.2-Exp and Claude Sonnet 4.5, by task and overall. The `n_trials` column gives the configured trial count even at 100%, where the full set is evaluated once and its standard deviation is zero. |
| `subsampling_task_tolerance_by_model.csv` | For each model and task, the fraction of subsets whose accuracy falls within the configured tolerance of that model's full-task accuracy. The default tolerance is ±5 percentage points. |
| `subsampling_task_tolerance_summary.csv` | Summaries by task across all 37 models at each fraction. The pooled pass rate averages the rates for individual models. |
