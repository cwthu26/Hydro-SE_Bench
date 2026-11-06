# Hydro-SE Bench software tests

The 24 tests in [test_scripts.py](test_scripts.py) check selected operations used in model evaluation and statistical analysis. They use small constructed datasets with known answers and simulated API responses, allowing readers to examine answer extraction, accuracy calculations, probability processing, and subsampling without collecting new model answers.

The examples use fictitious models and questions. No API key is required, and no requests are sent to commercial endpoints. These checks cover the cases described below; they do not rerun the paper's experiments or verify live endpoint availability. Instructions for analyzing the archived experimental data are in the [code guide](../code/README.md).

## Running the tests

From the repository root, use Python 3.10 or later:

```sh
python -m pip install -r requirements.txt
python -B -m unittest discover -s tests -v
```

The command lists each test and its outcome. A successful run ends with `Ran 24 tests` and `OK`. The tests use Python's built-in `unittest` module and the analysis dependencies already listed in `requirements.txt`. Temporary workbooks and CSV files are removed after each test; the archived benchmark and result files are not modified.

## 01 · Model evaluation and answer extraction — 5 tests

These tests examine [01hydrobench_model_test.py](../code/01hydrobench_model_test.py).

| Test | Content and purpose |
|---|---|
| Final-answer priority and option normalization | A reply mentions B in its discussion but ends with `FINAL ANSWER: C, A, C`. The extracted answer must be `AC`, with duplicate letters removed and the final-answer format recognized. This checks that an explicit final selection takes priority over the preceding discussion. |
| Empty reply | An empty reply must produce no extracted option. This checks that a missing answer is not turned into a selection. |
| Reference-answer exclusion | A distinctive reference-answer value is placed in a constructed question record. The outgoing request must omit that value and contain only a user message. This checks the request for this example without sending it to a model. |
| Recovery after a temporary request failure | The first simulated request fails and the second returns `FINAL ANSWER: A`. The result must record two attempts and answer A, without including the simulated API credential in the saved record. |
| Request-attempt limit | Every simulated request fails. With the limit set to three, the script must stop after three total attempts, including the initial request, and record an error. This checks the request budget within one evaluation round. |

## 02 · Overall accuracy — 4 tests

These tests examine [02bootstrap_overall_accuracy.py](../code/02bootstrap_overall_accuracy.py). The reference-answer check also applies to script 03.

| Test | Content and purpose |
|---|---|
| Accuracy denominator with blank predictions | A six-question workbook contains one model with six correct answers and another with three correct answers and three blanks. The correctness matrix must retain all six questions and record correct counts of six and three. This checks that blanks remain in the accuracy denominator. |
| Missing reference answers in scripts 02 and 03 | A workbook contains a missing reference answer. Both analysis scripts must reject it, preventing accuracy or pairwise comparisons from being calculated against an incomplete answer key. |
| Shared and repeatable bootstrap sampling | Two model columns have identical correct/incorrect patterns. Their accuracies must match in every bootstrap draw. Repeating the calculation with the same random seed must reproduce the same draws. This checks shared sampling across models and repeatability in the constructed example. |
| Accuracy CSV from a complete command | Script 02 runs on the six-question workbook with 100 bootstrap draws. Its output CSV must report accuracies of 100% and 50%, matching the known answers. This checks the path from workbook input to the saved accuracy table. |

## 03 · Paired model comparisons — 3 tests

These tests examine [03paired_bootstrap_comparisons.py](../code/03paired_bootstrap_comparisons.py).

| Test | Content and purpose |
|---|---|
| No difference between identical models | The observed accuracy difference and all bootstrap differences are zero. The two-sided centered-bootstrap P value must be 1, as expected when the constructed models have identical outcomes. |
| Holm adjustment | Input P values of 0.03, 0.01, and 0.04 must produce adjusted values of 0.06, 0.03, and 0.06 in the original order. These values can be checked by hand and test the multiple-comparison calculation. |
| Pairwise CSV from a complete command | Script 03 compares two models scoring 100% and 50% on the constructed workbook. It must write one pairwise result with a difference of 50 percentage points. |

## 04 · Confidence collection and calibration — 10 tests

These tests examine [04calibration.py](../code/04calibration.py).

| Test | Content and purpose |
|---|---|
| Probability boundaries and invalid text | The parser must accept `0`, `100`, and `50.5`, and reject `101` and `maybe 50`. This checks representative valid probabilities, the upper-bound restriction, and rejection of explanatory text. |
| Truncated probability reply | A numeric reply with a `length` finish reason must be excluded, even if its stored status is `ok`. This checks that an incomplete generation is not accepted solely because it contains a number. |
| Retrying an invalid probability reply | The simulated model first returns invalid text and then `75`. Collection must succeed on the second attempt with probability 75. Neither request may contain the reference-answer marker. |
| Missing probability file | A specified JSONL or XLSX file does not exist. Reading must fail with an error containing its path, distinguishing a missing file from an experiment with missing responses. |
| Missing file among multiple rounds | One supplied file exists and another is missing. Reading must fail regardless of their order, preventing analysis from silently using an incomplete set of first-pass and retest files. |
| Missing-file behavior through the analysis command | The analysis command receives a nonexistent response file. It must return a failure status, identify the missing file, and write no result CSV files in the new output directory. |
| Combining first-pass and retest answers | The first file contains responses for two question IDs; the retest supplies a new response for one of them. The new response must replace the matching ID while preserving the other question's response. |
| Invalid JSONL record | The second line of a response file contains invalid JSON. Reading must stop and identify the source file and line number, so malformed input is not silently omitted. |
| Matching question IDs across probability and status sheets | The probability workbook contains different question IDs in corresponding rows of its two worksheets. Reading must reject the mismatch, preventing a probability from being paired with another question's status. |
| Calibration tables from a complete command | The analysis command processes six questions, three with correct original answers and three with blank original answers. It must write three CSV tables, include three questions, exclude three blank originals, and place the three valid 100% confidence responses in the last of ten bins. With all included answers correct and confidence at 100%, ECE must be zero. |

## 05 · Subsampling stability — 2 tests

These tests examine [05subsampling.py](../code/05subsampling.py).

| Test | Content and purpose |
|---|---|
| Sampling without replacement and full-set inclusion | A constructed domain has ten questions in each task. A 30% sample must contain three distinct questions per task, and a 100% sample must contain every question. This checks sample size, uniqueness, and full-set inclusion. |
| Subsampling tables and deterministic full-set results | Script 05 runs on the constructed workbook with two models and three draws at each fraction below 100%. It must produce three CSV tables and 80 model/task/fraction rows in the accuracy table. At 100%, the standard deviation must be zero; the per-model tolerance table must report one subset and a 100% pass rate. |
