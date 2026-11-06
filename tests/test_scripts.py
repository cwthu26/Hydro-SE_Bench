"""Offline checks for the five evaluation and analysis scripts.

Run from the repository root: python -B -m unittest discover -s tests -v
HYDRO_TEST_TMPDIR optionally places temporary outputs outside the repository.
"""
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import URLError

import numpy as np
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]


def load_script(prefix):
    path = next((ROOT / "code").glob(prefix + "*.py"))
    spec = importlib.util.spec_from_file_location("script_" + prefix, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EVAL, OVERALL, PAIRED, CAL, SUB = [load_script(f"{i:02}") for i in range(1, 6)]


def response(content, finish="stop"):
    return io.BytesIO(json.dumps({"choices": [{"message": {"content": content},
                                             "finish_reason": finish}]}).encode())


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


class ScriptTests(unittest.TestCase):
    def setUp(self):
        parent = Path(os.environ.get("HYDRO_TEST_TMPDIR", ROOT / "results" / "test_tmp"))
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def workbook(self, missing_gold=False):
        book = Workbook()
        sheet = book.active
        sheet.title = "results"
        sheet.append(["id", "category_sheet", "level", "type", "question",
                      "gold_answer", "Model A", "Model B"])
        for i in range(6):
            sheet.append([f"q{i}", "Domain", "ABC"[i // 2], "single choice",
                          "Question", None if missing_gold and i == 0 else "A",
                          "A", "A" if i % 2 == 0 else None])
        path = self.folder / "answers.xlsx"
        book.save(path)
        book.close()
        return path

    def run_cli(self, module, *args):
        result = subprocess.run([sys.executable, "-B", module.__file__, *map(str, args)],
                                cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def evaluation_args(self):
        return SimpleNamespace(model="test-model", model_name="", language="en",
                               temperature=0, max_tokens=8192, thinking_parameter="none",
                               thinking="default", reasoning_effort="", timeout=1,
                               max_retries=3, api_url="https://example.invalid/test")

    def test_01_final_answer_has_priority_and_options_are_normalized(self):
        parsed = EVAL.extract_answer_details("Consider B.\nFINAL ANSWER: C, A, C")
        self.assertEqual(parsed["extracted_answer"], "AC")
        self.assertTrue(parsed["answer_format_ok"])

    def test_01_empty_reply_has_no_extracted_answer(self):
        self.assertEqual(EVAL.extract_answer_details("")["extracted_answer"], "")

    def test_01_request_does_not_include_reference_answer(self):
        example = {"ID": "q1", "type": "single choice", "input": "Choose A or B",
                   "target": "GOLD_SENTINEL"}
        body = EVAL.build_request_body(example, self.evaluation_args())
        self.assertNotIn("GOLD_SENTINEL", json.dumps(body))
        self.assertEqual([m["role"] for m in body["messages"]], ["user"])

    def test_01_transient_error_is_retried(self):
        example = {"ID": "q1", "type": "single choice", "input": "Choose A or B"}
        with patch.object(EVAL, "urlopen", side_effect=[URLError("offline"), response("FINAL ANSWER: A")]) as call, patch.object(EVAL.time, "sleep"):
            result = EVAL.evaluate_one(0, example, self.evaluation_args(), "test-only-key")
        self.assertEqual((call.call_count, result["attempts"], result["extracted_answer"]), (2, 2, "A"))
        self.assertNotIn("test-only-key", json.dumps(result))

    def test_01_request_budget_includes_initial_attempt(self):
        example = {"ID": "q1", "type": "single choice", "input": "Choose A or B"}
        with patch.object(EVAL, "urlopen", side_effect=URLError("offline")) as call, patch.object(EVAL.time, "sleep"):
            result = EVAL.evaluate_one(0, example, self.evaluation_args(), "test-only-key")
        self.assertEqual((call.call_count, result["attempts"], result["status"]), (3, 3, "error"))

    def test_02_known_accuracy_includes_blank_predictions(self):
        _, matrix, _ = OVERALL.load_correctness_matrix(self.workbook(), "results", 6)
        np.testing.assert_array_equal(matrix.sum(axis=0), [6, 3])
        self.assertEqual(matrix.shape, (6, 2))

    def test_02_and_03_reject_missing_reference_answers(self):
        path = self.workbook(missing_gold=True)
        for module in (OVERALL, PAIRED):
            with self.subTest(script=module.__file__), self.assertRaises(ValueError):
                module.load_correctness_matrix(path, "results", 6)

    def test_02_shared_bootstrap_preserves_identical_model_columns(self):
        matrix = np.array([[1, 1], [0, 0], [1, 1], [0, 0]], dtype=np.int8)
        draws = OVERALL.stratified_bootstrap_accuracy(matrix, [np.arange(4)], 100, 42, 2)
        np.testing.assert_array_equal(draws[:, 0], draws[:, 1])
        repeated = OVERALL.stratified_bootstrap_accuracy(matrix, [np.arange(4)], 100, 42, 2)
        np.testing.assert_array_equal(draws, repeated)

    def test_02_command_writes_known_accuracy(self):
        output = self.folder / "overall.csv"
        self.run_cli(OVERALL, "--input", self.workbook(), "--expected-questions", 6,
                     "--n-bootstrap", 100, "--output", output)
        rows = read_csv(output)
        self.assertEqual([float(row["Accuracy (%)"]) for row in rows], [100.0, 50.0])

    def test_03_identical_models_have_p_value_one(self):
        self.assertEqual(PAIRED.centered_bootstrap_p_value(np.zeros(100), 0), 1)

    def test_03_holm_adjustment_matches_hand_calculation(self):
        np.testing.assert_allclose(PAIRED.holm_adjust([0.03, 0.01, 0.04]), [0.06, 0.03, 0.06])

    def test_03_command_writes_one_pair_for_two_models(self):
        output = self.folder / "paired.csv"
        self.run_cli(PAIRED, "--input", self.workbook(), "--expected-questions", 6,
                     "--n-bootstrap", 100, "--top-models", 2, "--output", output)
        rows = read_csv(output)
        self.assertEqual(len(rows), 1)
        self.assertEqual(float(rows[0]["Difference (pp)"]), 50)

    def test_04_probability_boundaries_and_invalid_text(self):
        for raw, expected in [("0", 0), ("100", 100), ("50.5", 50.5), ("101", None), ("maybe 50", None)]:
            with self.subTest(raw=raw):
                self.assertEqual(CAL.parse_probability(raw), expected)

    def test_04_truncated_probability_is_not_valid(self):
        self.assertFalse(CAL.is_valid_response({"status": "ok", "raw_probability": "80", "finish_reason": "length"}))

    def test_04_collection_retries_invalid_reply_without_sending_gold(self):
        row = {"id": "q1", "question_type": "single choice", "question": "Choose A or B",
               "model_answer": "A", "gold_answer": "GOLD_SENTINEL"}
        args = SimpleNamespace(api_model="test", model_column="Model A", temperature=0,
                               max_tokens=2048, top_p=None, reasoning_json="", timeout=1,
                               max_retries=3, api_url="https://example.invalid/test")
        with patch.object(CAL, "urlopen", side_effect=[response("invalid"), response("75")]) as call, patch.object(CAL.time, "sleep"):
            result = CAL.collect_one(row, args, "test-only-key")
        self.assertEqual((result["status"], result["attempts"], result["probability_percent"]), ("ok", 2, 75))
        for request in call.call_args_list:
            self.assertNotIn(b"GOLD_SENTINEL", request.args[0].data)

    def test_04_missing_response_file_must_raise(self):
        # A mistyped input path must not silently become an empty experiment.
        for name in ("missing.jsonl", "missing.xlsx"):
            missing = self.folder / name
            with self.subTest(name=name):
                with self.assertRaises(FileNotFoundError) as error:
                    CAL.load_responses(missing, "Model A")
                self.assertIn(str(missing), str(error.exception))

    def test_04_missing_file_in_multiple_rounds_must_raise(self):
        first = self.folder / "first.jsonl"
        first.write_text(json.dumps({"id": "q0", "raw_probability": "75"}), encoding="utf-8")
        missing = self.folder / "missing_retest.jsonl"
        for sources in ([first, missing], [missing, first]):
            with self.subTest(sources=sources), self.assertRaises(FileNotFoundError):
                CAL.load_responses(sources)

    def test_04_missing_file_command_fails_without_result_tables(self):
        missing = self.folder / "missing_retest.jsonl"
        output = self.folder / "failed_analysis"
        result = subprocess.run(
            [sys.executable, "-B", CAL.__file__, "analyze", "--input", str(self.workbook()),
             "--model-column", "Model A", "--responses", str(missing), "--output-dir", str(output)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(missing.name, result.stderr)
        self.assertEqual(list(output.glob("*.csv")), [])

    def test_04_retest_replaces_matching_id_and_preserves_other_answers(self):
        first, retest = self.folder / "first.jsonl", self.folder / "retest.jsonl"
        first.write_text('\n'.join(json.dumps({"id": q, "raw_probability": p})
                                   for q, p in [("q0", "10"), ("q1", "20")]), encoding="utf-8")
        retest.write_text(json.dumps({"id": "q0", "raw_probability": "90"}), encoding="utf-8")
        merged = CAL.load_responses([first, retest])
        self.assertEqual({q: r["raw_probability"] for q, r in merged.items()}, {"q0": "90", "q1": "20"})

    def test_04_malformed_jsonl_reports_source_and_line(self):
        source = self.folder / "malformed.jsonl"
        source.write_text('{"id": "q0"}\nnot valid json\n', encoding="utf-8")
        with self.assertRaises(ValueError) as error:
            CAL.load_responses(source)
        self.assertIn(f"{source}:2", str(error.exception))

    def probability_workbook(self, probability_ids, status_ids):
        book = Workbook()
        probabilities = book.active
        probabilities.title = "probabilities"
        statuses = book.create_sheet("response_status")
        for sheet in (probabilities, statuses):
            sheet.append(["id", "Model A"])
        for question_id in probability_ids:
            probabilities.append([question_id, 75])
        for question_id in status_ids:
            statuses.append([question_id, "ok"])
        path = self.folder / "probabilities.xlsx"
        book.save(path)
        book.close()
        return path

    def test_04_probability_and_status_ids_must_match(self):
        source = self.probability_workbook(["q0"], ["different_question"])
        with self.assertRaises(ValueError):
            CAL.load_responses(source, "Model A")

    def test_04_command_outputs_three_tables_and_excludes_blanks(self):
        source = self.folder / "responses.jsonl"
        source.write_text("\n".join(json.dumps({"id": f"q{i}", "status": "ok",
                           "finish_reason": "stop", "raw_probability": "100"}) for i in range(6)), encoding="utf-8")
        output = self.folder / "calibration"
        self.run_cli(CAL, "analyze", "--input", self.workbook(), "--model-column", "Model B",
                     "--responses", source, "--output-dir", output)
        self.assertEqual(len(list(output.glob("*.csv"))), 3)
        summary = read_csv(output / "calibration_probability_summary.csv")[0]
        self.assertEqual((int(summary["analyzed_questions"]), int(summary["truncated_original_answer"])), (3, 3))
        self.assertEqual(float(summary["ece_percent"]), 0)
        bins = read_csv(output / "calibration_probability_bins.csv")
        self.assertEqual((len(bins), int(bins[-1]["n"])), (10, 3))

    def test_05_sampling_has_no_duplicates_and_full_set_is_complete(self):
        groups = {"Domain": {task: list(range(i * 10, (i + 1) * 10)) for i, task in enumerate("ABC")}}
        partial = SUB.sampled_indices(groups, 30, 0, 42)
        full = SUB.sampled_indices(groups, 100, 0, 42)
        for task in "ABC":
            self.assertEqual(len(set(partial[task])), 3)
            np.testing.assert_array_equal(full[task], groups["Domain"][task])

    def subsampling_outputs(self):
        output = self.folder / "subsampling"
        self.run_cli(SUB, "--input", self.workbook(), "--output-dir", output,
                     "--trials", 3, "--figure-models", "Model A", "Model B")
        return output

    def test_05_command_outputs_tables_with_deterministic_full_set(self):
        output = self.subsampling_outputs()
        self.assertEqual(len(list(output.glob("*.csv"))), 3)
        rows = read_csv(output / "subsampling_accuracy.csv")
        self.assertEqual(len(rows), 80)
        for row in rows:
            if row["sample_ratio_percent"] == "100":
                self.assertEqual(float(row["std_accuracy_percent"]), 0)
        detail = read_csv(output / "subsampling_task_tolerance_by_model.csv")
        for row in detail:
            if row["sample_ratio_percent"] == "100":
                self.assertEqual((int(row["n_subsets"]), float(row["pass_rate_percent"])), (1, 100))



if __name__ == "__main__":
    unittest.main()
