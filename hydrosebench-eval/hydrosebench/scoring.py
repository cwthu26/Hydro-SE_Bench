from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from itertools import zip_longest
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore[assignment]

_CHOICE_PATTERN = re.compile(r"[A-Z]+|[A-Z](?:[\s,，;；/、+|]+[A-Z])+")
_NO_CORRECT_OPTION_ANSWERS = {"无正确选项", "无正确答案"}
_ISSUE_MESSAGES = {
    "missing_standard_answer": "Missing standard answer",
    "invalid_standard_answer": "Standard answer contains an option absent from the question",
    "missing_model_answer": "Missing model answer",
    "unparseable_model_answer": "Cannot parse a definite model answer",
    "invalid_model_answer": "Model answer contains an option absent from the question",
}


def _format_accuracy(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2%}"


@dataclass(slots=True, frozen=True)
class ExampleScore:
    example_id: str
    expected: tuple[str, ...]
    predicted: tuple[str, ...]
    is_correct: bool | None
    missing_prediction: bool
    raw_prediction: Any = None
    metadata: Mapping[str, Any] | None = None
    issues: tuple[str, ...] = ()

    @property
    def status(self) -> str:
        if self.is_correct is None:
            return "Unscored"
        return "Correct" if self.is_correct else "Incorrect"

    @property
    def reason(self) -> str:
        return "; ".join(_ISSUE_MESSAGES[issue] for issue in self.issues)


class ScoreReport:
    def __init__(
        self,
        *,
        benchmark_name: str | None,
        example_scores: Sequence[ExampleScore],
    ) -> None:
        self.benchmark_name = benchmark_name
        self.example_scores = list(example_scores)

    # Summary stats ----------------------------------------------------- #
    @property
    def max_score(self) -> int:
        return sum(s.is_correct is not None for s in self.example_scores)

    @property
    def total_questions(self) -> int:
        return len(self.example_scores)

    @property
    def unscored_count(self) -> int:
        return self.total_questions - self.max_score

    @property
    def incorrect_count(self) -> int:
        return sum(s.is_correct is False for s in self.example_scores)

    @property
    def issue_counts(self) -> dict[str, int]:
        return dict(Counter(issue for s in self.example_scores for issue in s.issues))

    @property
    def issues(self) -> list[dict[str, Any]]:
        return [{"id": s.example_id, "issues": s.issues, "reason": s.reason}
                for s in self.example_scores if s.issues]

    @property
    def total_score(self) -> int:
        return sum(1 for s in self.example_scores if s.is_correct)

    @property
    def accuracy(self) -> float | None:
        if not self.max_score:
            return None
        return self.total_score / self.max_score

    def summary(self) -> str:
        name = self.benchmark_name or "Benchmark"
        return (
            f"{name}: {self.total_score}/{self.max_score} "
            f"({_format_accuracy(self.accuracy)} accuracy; "
            f"{self.max_score}/{self.total_questions} scored, {self.unscored_count} unscored)"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark": self.benchmark_name,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "accuracy": self.accuracy,
            "total_questions": self.total_questions,
            "incorrect_count": self.incorrect_count,
            "unscored_count": self.unscored_count,
            "issue_counts": self.issue_counts,
            "issues": self.issues,
            "examples": [
                {
                    "id": s.example_id,
                    "expected": s.expected,
                    "predicted": s.predicted,
                    "is_correct": s.is_correct,
                    "missing_prediction": s.missing_prediction,
                    "status": s.status,
                    "issues": s.issues,
                    "reason": s.reason,
                    "metadata": dict(s.metadata or {}),
                    "raw_prediction": None if _is_missing_answer(s.raw_prediction) else s.raw_prediction,
                }
                for s in self.example_scores
            ],
        }

    def to_json(self, *, ensure_ascii: bool = False, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, indent=indent)

    def to_issues_csv(self, output_path: str | Path) -> Path:
        output_path = Path(output_path)
        with output_path.open("w", encoding="utf-8-sig", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=[
                "ID", "Issue Codes", "Issue Details", "Correct Answer", "Model Answer",
            ])
            writer.writeheader()
            for score in self.example_scores:
                if score.issues:
                    writer.writerow({
                        "ID": score.example_id,
                        "Issue Codes": ",".join(score.issues),
                        "Issue Details": score.reason,
                        "Correct Answer": ",".join(score.expected),
                        "Model Answer": "" if score.raw_prediction is None else str(score.raw_prediction),
                    })
        return output_path

    def get_category_stats(self, benchmark: Any | None = None) -> dict[str, dict[str, Any]]:
        """
        Calculate accuracy statistics by category.
        
        Args:
            benchmark: Benchmark object, used to get question category information
        
        Returns:
            Dictionary with category names as keys and statistics dictionaries as values
        """
        category_stats: dict[str, dict[str, int]] = {}
        
        for score in self.example_scores:
            category = None
            if benchmark is not None:
                for ex in benchmark.examples:
                    if ex.id == score.example_id:
                        category = ex.category
                        break
            elif score.metadata:
                category = score.metadata.get("category")
            
            category = str(category) if category else "Unknown"
            
            if category not in category_stats:
                category_stats[category] = {"total": 0, "scored": 0, "correct": 0}
            
            category_stats[category]["total"] += 1
            category_stats[category]["scored"] += int(score.is_correct is not None)
            if score.is_correct:
                category_stats[category]["correct"] += 1
        
        # Calculate accuracy
        result = {}
        for category, stats in category_stats.items():
            accuracy = stats["correct"] / stats["scored"] if stats["scored"] else None
            result[category] = {
                "total": stats["total"],
                "correct": stats["correct"],
                "incorrect": stats["scored"] - stats["correct"],
                "scored": stats["scored"],
                "unscored": stats["total"] - stats["scored"],
                "accuracy": accuracy,
            }
        
        return result

    def get_level_stats(self, benchmark: Any | None = None) -> dict[str, dict[str, Any]]:
        """
        Calculate accuracy statistics by difficulty level.
        
        Args:
            benchmark: Benchmark object, used to get question difficulty information
        
        Returns:
            Dictionary with difficulty levels as keys and statistics dictionaries as values
        """
        level_stats: dict[str, dict[str, int]] = {}
        
        for score in self.example_scores:
            level = None
            if benchmark is not None:
                for ex in benchmark.examples:
                    if ex.id == score.example_id:
                        level = ex.level
                        break
            elif score.metadata:
                level = score.metadata.get("level")
            
            level = str(level) if level else "Unknown"
            
            if level not in level_stats:
                level_stats[level] = {"total": 0, "scored": 0, "correct": 0}
            
            level_stats[level]["total"] += 1
            level_stats[level]["scored"] += int(score.is_correct is not None)
            if score.is_correct:
                level_stats[level]["correct"] += 1
        
        # Calculate accuracy
        result = {}
        for level, stats in level_stats.items():
            accuracy = stats["correct"] / stats["scored"] if stats["scored"] else None
            result[level] = {
                "total": stats["total"],
                "correct": stats["correct"],
                "incorrect": stats["scored"] - stats["correct"],
                "scored": stats["scored"],
                "unscored": stats["total"] - stats["scored"],
                "accuracy": accuracy,
            }
        
        return result

    def get_type_stats(self, benchmark: Any | None = None) -> dict[str, dict[str, Any]]:
        """
        Calculate accuracy statistics by question type.
        
        Args:
            benchmark: Benchmark object, used to get question type information
        
        Returns:
            Dictionary with question type names as keys and statistics dictionaries as values
        """
        type_stats: dict[str, dict[str, int]] = {}
        
        for score in self.example_scores:
            qtype = None
            if benchmark is not None:
                for ex in benchmark.examples:
                    if ex.id == score.example_id:
                        qtype = ex.question_type
                        break
            elif score.metadata:
                qtype = score.metadata.get("type")
            
            qtype = str(qtype) if qtype else "Unknown"
            
            if qtype not in type_stats:
                type_stats[qtype] = {"total": 0, "scored": 0, "correct": 0}
            
            type_stats[qtype]["total"] += 1
            type_stats[qtype]["scored"] += int(score.is_correct is not None)
            if score.is_correct:
                type_stats[qtype]["correct"] += 1
        
        # Calculate accuracy
        result = {}
        for qtype, stats in type_stats.items():
            accuracy = stats["correct"] / stats["scored"] if stats["scored"] else None
            result[qtype] = {
                "total": stats["total"],
                "correct": stats["correct"],
                "incorrect": stats["scored"] - stats["correct"],
                "scored": stats["scored"],
                "unscored": stats["total"] - stats["scored"],
                "accuracy": accuracy,
            }
        
        return result

    def to_csv(
        self,
        output_path: str | Path,
        *,
        benchmark: Any | None = None,
    ) -> Path:
        """
        Export to CSV format, including detailed information such as questions, correct answers, and model answers.
        
        Args:
            output_path: Output file path
            benchmark: Optional Benchmark object, used to get detailed information such as question content
        
        Returns:
            Output file path
        """
        if pd is None:
            raise ImportError(
                "pandas is required for CSV export. Install it with: pip install pandas"
            )
        
        output_path = Path(output_path)
        
        # Build data rows (same as to_excel)
        rows = []
        for score in self.example_scores:
            # Get question content (if benchmark is available)
            question_text = ""
            category = None
            level = None
            question_type = None
            
            if benchmark is not None:
                # Find corresponding question from benchmark
                example = None
                for ex in benchmark.examples:
                    if ex.id == score.example_id:
                        example = ex
                        break
                
                if example:
                    question_text = example.input_text
                    category = example.category
                    level = example.level
                    question_type = example.question_type
            
            # Format answers
            expected_str = ",".join(sorted(score.expected)) if score.expected else "(None)"
            
            # Show raw input value, if missing show "(Missing)"
            if score.missing_prediction:
                predicted_str = "(Missing)"
            elif score.predicted:
                # If valid answer can be parsed, show parsed answer
                predicted_str = ",".join(sorted(score.predicted))
            else:
                # If cannot parse but raw value exists, show raw value directly
                if score.raw_prediction is not None:
                    # Show raw input value
                    if isinstance(score.raw_prediction, str):
                        predicted_str = score.raw_prediction
                    else:
                        predicted_str = str(score.raw_prediction)
                else:
                    predicted_str = "(Missing)"
            
            rows.append({
                "ID": score.example_id,
                "Question": question_text,
                "Category": category or "",
                "Level": level or "",
                "Type": question_type or "",
                "Correct Answer": expected_str,
                "Model Answer": predicted_str,
                "Is Correct": "N/A" if score.is_correct is None else ("✓" if score.is_correct else "✗"),
                "Status": score.status,
                "Raw Model Answer": "" if score.raw_prediction is None else str(score.raw_prediction),
                "Issue Codes": ",".join(score.issues),
                "Issue Details": score.reason,
            })
        
        # Create DataFrame and save as CSV
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")  # Use utf-8-sig for Excel to open correctly
        
        return output_path

    def to_excel(
        self,
        output_path: str | Path,
        *,
        benchmark: Any | None = None,
    ) -> Path:
        """
        Export to Excel format, including detailed information such as questions, correct answers, and model answers.
        
        Args:
            output_path: Output file path
            benchmark: Optional Benchmark object, used to get detailed information such as question content
        
        Returns:
            Output file path
        """
        if pd is None:
            raise ImportError(
                "pandas is required for Excel export. Install it with: pip install pandas openpyxl"
            )
        
        output_path = Path(output_path)
        
        # Build data rows
        rows = []
        for score in self.example_scores:
            # Get question content (if benchmark is available)
            question_text = ""
            category = None
            level = None
            question_type = None
            
            if benchmark is not None:
                # Find corresponding question from benchmark
                example = None
                for ex in benchmark.examples:
                    if ex.id == score.example_id:
                        example = ex
                        break
                
                if example:
                    question_text = example.input_text
                    category = example.category
                    level = example.level
                    question_type = example.question_type
            
            # Format answers
            expected_str = ",".join(sorted(score.expected)) if score.expected else "(None)"
            
            # Show raw input value, if missing show "(Missing)"
            if score.missing_prediction:
                predicted_str = "(Missing)"
            elif score.predicted:
                # If valid answer can be parsed, show parsed answer
                predicted_str = ",".join(sorted(score.predicted))
            else:
                # If cannot parse but raw value exists, show raw value directly
                if score.raw_prediction is not None:
                    # Show raw input value
                    if isinstance(score.raw_prediction, str):
                        predicted_str = score.raw_prediction
                    else:
                        predicted_str = str(score.raw_prediction)
                else:
                    predicted_str = "(Missing)"
            
            rows.append({
                "ID": score.example_id,
                "Question": question_text,
                "Category": category or "",
                "Level": level or "",
                "Type": question_type or "",
                "Correct Answer": expected_str,
                "Model Answer": predicted_str,
                "Is Correct": "N/A" if score.is_correct is None else ("✓" if score.is_correct else "✗"),
                "Status": score.status,
                "Raw Model Answer": "" if score.raw_prediction is None else str(score.raw_prediction),
                "Issue Codes": ",".join(score.issues),
                "Issue Details": score.reason,
            })
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Write to Excel
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Evaluation Results", index=False)
            
            # Set column widths
            worksheet = writer.sheets["Evaluation Results"]
            worksheet.column_dimensions["A"].width = 15  # ID
            worksheet.column_dimensions["B"].width = 50  # Question
            worksheet.column_dimensions["C"].width = 15  # Category
            worksheet.column_dimensions["D"].width = 12  # Level
            worksheet.column_dimensions["E"].width = 12  # Type
            worksheet.column_dimensions["F"].width = 15  # Correct Answer
            worksheet.column_dimensions["G"].width = 15  # Model Answer
            worksheet.column_dimensions["H"].width = 10  # Is Correct
            worksheet.column_dimensions["I"].width = 12  # Status
            worksheet.column_dimensions["J"].width = 30  # Raw Model Answer
            worksheet.column_dimensions["K"].width = 30  # Issue Codes
            worksheet.column_dimensions["L"].width = 60  # Issue Details
            issue_rows = [{"ID": item["id"], "Issue Codes": ",".join(item["issues"]),
                           "Issue Details": item["reason"]} for item in self.issues]
            pd.DataFrame(issue_rows, columns=["ID", "Issue Codes", "Issue Details"]).to_excel(
                writer, sheet_name="Issues", index=False)
            writer.sheets["Issues"].column_dimensions["A"].width = 15
            writer.sheets["Issues"].column_dimensions["B"].width = 35
            writer.sheets["Issues"].column_dimensions["C"].width = 75
            
            # Add summary information
            summary_row = len(df) + 3
            worksheet.cell(summary_row, 1, "Summary")
            worksheet.cell(summary_row + 1, 1, "Benchmark: hydrosebench")
            worksheet.cell(summary_row + 2, 1, f"Total Questions: {self.total_questions}")
            worksheet.cell(summary_row + 3, 1, f"Correct: {self.total_score}")
            worksheet.cell(summary_row + 4, 1, f"Incorrect: {self.max_score - self.total_score}")
            worksheet.cell(summary_row + 5, 1, f"Accuracy: {_format_accuracy(self.accuracy)}")
            worksheet.cell(summary_row + 6, 1, f"Scored: {self.max_score}")
            worksheet.cell(summary_row + 7, 1, f"Unscored: {self.unscored_count}")
            
            # Add worksheet with statistics by category
            category_stats = self.get_category_stats(benchmark)
            if category_stats:
                category_rows = []
                for category, stats in sorted(category_stats.items()):
                    category_rows.append({
                        "Category": category,
                        "Total": stats["total"],
                        "Correct": stats["correct"],
                        "Incorrect": stats["incorrect"],
                        "Accuracy": _format_accuracy(stats['accuracy']),
                        "Scored": stats["scored"],
                        "Unscored": stats["unscored"],
                    })
                
                category_df = pd.DataFrame(category_rows)
                # Excel worksheet name limited to 31 characters
                sheet_name = "By Category"[:31]
                category_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Set column widths
                cat_worksheet = writer.sheets[sheet_name]
                cat_worksheet.column_dimensions["A"].width = 30
                cat_worksheet.column_dimensions["B"].width = 12
                cat_worksheet.column_dimensions["C"].width = 12
                cat_worksheet.column_dimensions["D"].width = 12
                cat_worksheet.column_dimensions["E"].width = 12
                cat_worksheet.column_dimensions["F"].width = 12
                cat_worksheet.column_dimensions["G"].width = 12
                
                # Add summary information
                summary_row = len(category_df) + 3
                cat_worksheet.cell(summary_row, 1, "Summary")
                cat_worksheet.cell(summary_row + 1, 1, f"Total Categories: {len(category_stats)}")
                total_questions = sum(s["total"] for s in category_stats.values())
                total_correct = sum(s["correct"] for s in category_stats.values())
                cat_worksheet.cell(summary_row + 2, 1, f"Total Questions: {total_questions}")
                cat_worksheet.cell(summary_row + 3, 1, f"Total Correct: {total_correct}")
                total_scored = sum(s["scored"] for s in category_stats.values())
                overall_acc = total_correct / total_scored if total_scored else None
                cat_worksheet.cell(summary_row + 4, 1, f"Overall Accuracy: {_format_accuracy(overall_acc)}")
                cat_worksheet.cell(summary_row + 5, 1, f"Scored: {total_scored}")
                cat_worksheet.cell(summary_row + 6, 1, f"Unscored: {total_questions - total_scored}")
            
            # Add worksheet with statistics by difficulty level
            level_stats = self.get_level_stats(benchmark)
            if level_stats:
                level_rows = []
                for level, stats in sorted(level_stats.items()):
                    level_rows.append({
                        "Level": level,
                        "Total": stats["total"],
                        "Correct": stats["correct"],
                        "Incorrect": stats["incorrect"],
                        "Accuracy": _format_accuracy(stats['accuracy']),
                        "Scored": stats["scored"],
                        "Unscored": stats["unscored"],
                    })
                
                level_df = pd.DataFrame(level_rows)
                # Excel worksheet name limited to 31 characters
                sheet_name = "By Level"[:31]
                level_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Set column widths
                level_worksheet = writer.sheets[sheet_name]
                level_worksheet.column_dimensions["A"].width = 30
                level_worksheet.column_dimensions["B"].width = 12
                level_worksheet.column_dimensions["C"].width = 12
                level_worksheet.column_dimensions["D"].width = 12
                level_worksheet.column_dimensions["E"].width = 12
                level_worksheet.column_dimensions["F"].width = 12
                level_worksheet.column_dimensions["G"].width = 12
                
                # Add summary information
                summary_row = len(level_df) + 3
                level_worksheet.cell(summary_row, 1, "Summary")
                level_worksheet.cell(summary_row + 1, 1, f"Total Levels: {len(level_stats)}")
                total_questions = sum(s["total"] for s in level_stats.values())
                total_correct = sum(s["correct"] for s in level_stats.values())
                level_worksheet.cell(summary_row + 2, 1, f"Total Questions: {total_questions}")
                level_worksheet.cell(summary_row + 3, 1, f"Total Correct: {total_correct}")
                total_scored = sum(s["scored"] for s in level_stats.values())
                overall_acc = total_correct / total_scored if total_scored else None
                level_worksheet.cell(summary_row + 4, 1, f"Overall Accuracy: {_format_accuracy(overall_acc)}")
                level_worksheet.cell(summary_row + 5, 1, f"Scored: {total_scored}")
                level_worksheet.cell(summary_row + 6, 1, f"Unscored: {total_questions - total_scored}")
            
            # Add worksheet with statistics by question type
            type_stats = self.get_type_stats(benchmark)
            if type_stats:
                type_rows = []
                for qtype, stats in sorted(type_stats.items()):
                    type_rows.append({
                        "Type": qtype,
                        "Total": stats["total"],
                        "Correct": stats["correct"],
                        "Incorrect": stats["incorrect"],
                        "Accuracy": _format_accuracy(stats['accuracy']),
                        "Scored": stats["scored"],
                        "Unscored": stats["unscored"],
                    })
                
                type_df = pd.DataFrame(type_rows)
                sheet_name = "By Type"[:31]
                type_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Set column widths
                type_worksheet = writer.sheets[sheet_name]
                type_worksheet.column_dimensions["A"].width = 30
                type_worksheet.column_dimensions["B"].width = 12
                type_worksheet.column_dimensions["C"].width = 12
                type_worksheet.column_dimensions["D"].width = 12
                type_worksheet.column_dimensions["E"].width = 12
                type_worksheet.column_dimensions["F"].width = 12
                type_worksheet.column_dimensions["G"].width = 12
                
                # Add summary information
                summary_row = len(type_df) + 3
                type_worksheet.cell(summary_row, 1, "Summary")
                type_worksheet.cell(summary_row + 1, 1, f"Total Types: {len(type_stats)}")
                total_questions = sum(s["total"] for s in type_stats.values())
                total_correct = sum(s["correct"] for s in type_stats.values())
                type_worksheet.cell(summary_row + 2, 1, f"Total Questions: {total_questions}")
                type_worksheet.cell(summary_row + 3, 1, f"Total Correct: {total_correct}")
                total_scored = sum(s["scored"] for s in type_stats.values())
                overall_acc = total_correct / total_scored if total_scored else None
                type_worksheet.cell(summary_row + 4, 1, f"Overall Accuracy: {_format_accuracy(overall_acc)}")
                type_worksheet.cell(summary_row + 5, 1, f"Scored: {total_scored}")
                type_worksheet.cell(summary_row + 6, 1, f"Unscored: {total_questions - total_scored}")
        
        return output_path

    def to_markdown(
        self,
        output_path: str | Path | None = None,
        *,
        benchmark: Any | None = None,
        max_rows: int | None = None,
    ) -> str:
        """
        Export as Markdown table format for easy viewing and sharing.
        
        Args:
            output_path: Optional output file path, if not provided only returns string
            benchmark: Optional Benchmark object, used to get detailed information such as question content
            max_rows: Maximum number of rows to display, None means display all
        
        Returns:
            Markdown format string
        """
        lines = []
        
        # Title
        lines.append(f"# {self.benchmark_name or 'Evaluation Report'}")
        lines.append("")
        lines.append(f"**Summary**: {self.summary()}")
        lines.append("")
        
        # Table header
        headers = ["ID", "Question", "Category", "Level", "Correct Answer", "Model Answer", "Result", "Issue Details"]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        # Table content
        scores_to_show = self.example_scores[:max_rows] if max_rows else self.example_scores
        for score in scores_to_show:
            # Get question content
            question_text = ""
            category = ""
            level = ""
            
            if benchmark is not None:
                example = None
                for ex in benchmark.examples:
                    if ex.id == score.example_id:
                        example = ex
                        break
                
                if example:
                    # Truncate overly long questions
                    question_text = example.input_text[:50] + "..." if len(example.input_text) > 50 else example.input_text
                    category = str(example.category) if example.category else ""
                    level = str(example.level) if example.level else ""
            
            # Format answers
            expected_str = ",".join(sorted(score.expected)) if score.expected else "(None)"
            predicted_str = str(score.raw_prediction) if not score.missing_prediction else "(Missing)"
            
            # Result marker
            result = score.status
            
            row = [
                score.example_id,
                question_text or "-",
                category or "-",
                level or "-",
                expected_str,
                predicted_str,
                result,
                score.reason,
            ]
            lines.append("| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", "<br>") for cell in row) + " |")
        
        if max_rows and len(self.example_scores) > max_rows:
            lines.append("")
            lines.append(f"*(Showing first {max_rows} of {len(self.example_scores)} entries)*")
        
        markdown_text = "\n".join(lines)
        
        # If output path is provided, write to file
        if output_path:
            Path(output_path).write_text(markdown_text, encoding="utf-8")
        
        return markdown_text


# ---------------------------------------------------------------------- #
# Public scoring helpers
# ---------------------------------------------------------------------- #
def score_examples(
    examples: Sequence[Any],
    predictions: Any,
    *,
    benchmark_name: str | None = None,
) -> ScoreReport:
    normalized_predictions, is_mapping = _normalize_prediction_input(predictions)

    duplicate_ids = [key for key, count in Counter(e.id for e in examples).items() if count > 1]
    if duplicate_ids:
        raise ValueError(f"Duplicate benchmark IDs: {', '.join(duplicate_ids)}")
    scores: list[ExampleScore] = []
    for idx, example in enumerate(examples):
        issues = []
        if not example.correct_options:
            issues.append("missing_standard_answer")
        option_labels = _question_option_labels(example.input_text)
        if option_labels and not set(example.correct_options) <= option_labels:
            issues.append("invalid_standard_answer")
        raw = (normalized_predictions.get(example.id) if is_mapping else
               normalized_predictions[idx] if idx < len(normalized_predictions) else None)
        missing = _is_missing_answer(raw)
        predicted = () if missing else _normalize_answer(raw)
        if missing:
            issues.append("missing_model_answer")
        elif not predicted:
            issues.append("unparseable_model_answer")
        elif (option_labels and not set(predicted) <= option_labels
              and not (len(predicted) == 1 and predicted[0] in _NO_CORRECT_OPTION_ANSWERS)):
            issues.append("invalid_model_answer")
        expected = tuple(example.correct_options)
        scores.append(ExampleScore(
            example_id=example.id,
            expected=expected,
            predicted=predicted,
            is_correct=None if issues else set(predicted) == set(expected),
            missing_prediction=missing,
            raw_prediction=raw,
            metadata=getattr(example, "metadata", None),
            issues=tuple(issues),
        ))

    return ScoreReport(benchmark_name=benchmark_name, example_scores=scores)


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #
def _question_option_labels(text: str) -> set[str]:
    start = re.search(r"\n[ \t]*(A)(?=[\s\\\u4e00-\u9fff.．、：:,，）)])", text) or re.search(r"\n[ \t]*([A-Z])(?=[\s\\\u4e00-\u9fff.．、：:,，）)])", text)
    if start:
        text = text[start.start():]
    labels = []
    for a, b in re.findall(
        r"(?m)^[ \t]*([A-Z])(?=[\s\\\u4e00-\u9fff])|(?<![a-zA-Z])([A-Z])[ \t]*[.．、：:,，）)]",
        text,
    ):
        if (a or b) == chr(ord(start.group(1) if start else 'A') + len(labels)):
            labels.append(a or b)
    return set(labels)


def _is_missing_answer(raw: Any) -> bool:
    if raw is None:
        return True
    if isinstance(raw, str):
        return not raw.strip() or raw.strip().lower() in {"nan", "null", "none", "n/a"}
    if isinstance(raw, float):
        return math.isnan(raw)
    if pd is not None and raw is pd.NA:
        return True
    if isinstance(raw, Mapping):
        for key in ("answer", "answers", "choices", "prediction", "output"):
            if key in raw:
                return _is_missing_answer(raw[key])
        return not raw
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        return not raw or all(_is_missing_answer(item) for item in raw)
    return False


def _normalize_prediction_input(predictions: Any) -> tuple[Any, bool]:
    if isinstance(predictions, Mapping):
        return predictions, True

    if isinstance(predictions, Sequence) and not isinstance(predictions, (str, bytes)):
        seq = list(predictions)
        if any(isinstance(item, Mapping) and "id" in item for item in seq):
            mapping: dict[str, Any] = {}
            for item in seq:
                if not isinstance(item, Mapping):
                    raise TypeError("Prediction list must be uniform")
                if "id" not in item:
                    raise KeyError("Prediction entry missing 'id'")
                if str(item["id"]) in mapping:
                    raise ValueError(f"Duplicate prediction ID: {item['id']}")
                mapping[str(item["id"])] = next(
                    (item[key] for key in ("answer", "answers", "choices", "prediction", "output") if key in item),
                    None,
                )
            return mapping, True
        return seq, False

    raise TypeError(
        "Predictions must be a mapping of {question_id: answer} or a "
        "sequence following the benchmark order."
    )


def _normalize_answer(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return tuple()

    if isinstance(raw, str):
        text = raw.strip()
        if text.casefold() in {"timeout", "error", "unknown", "no answer", "i do not know"}:
            return tuple()
        text = re.sub(r"^(?:(?:the\s+)?(?:correct\s+)?answer\s*(?:is\s*)?[:：]?\s*|(?:正确)?答案\s*[:：]?\s*)",
                      "", text, flags=re.IGNORECASE).strip().rstrip(".。")
        if text in _NO_CORRECT_OPTION_ANSWERS:
            return (text,)
        if not _CHOICE_PATTERN.fullmatch(text.upper()):
            return tuple()
        # A compact answer is a sequence of labels, not a word such as Timeout.
        if text.isalpha() and len(text) > 1 and not text.isupper():
            return tuple()
        return tuple(dict.fromkeys(re.findall(r"[A-Z]", text.upper())))

    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        letters: list[str] = []
        for item in raw:
            parsed = _normalize_answer(item)
            if not parsed:
                return tuple()
            letters.extend(parsed)
        if any(answer in _NO_CORRECT_OPTION_ANSWERS for answer in letters) and len(set(letters)) > 1:
            return tuple()
        return tuple(dict.fromkeys(letters))

    if isinstance(raw, Mapping):
        for key in ("answer", "answers", "choices", "prediction", "output"):
            if key in raw:
                return _normalize_answer(raw[key])
        return tuple()

    return tuple()

