"""Public package interface for the HydroSEBench evaluation helpers."""

__version__ = "0.1.0"

from .benchmark import Benchmark, Example
from .datasets import BUILTIN_BENCHMARKS, download_hydrosebench_data, load_builtin_benchmark
from .excel_loader import load_benchmark_from_file, load_predictions_from_excel
from .scoring import ExampleScore, ScoreReport
from .batch_evaluate import evaluate_all_models, identify_model_columns
from .sampling import sample_examples_by_category, sample_benchmark_by_category, save_benchmark
from .reporting import (
    create_summary_excel,
    validate_data_quality,
    generate_analysis_report,
)

__all__ = [
    "__version__",
    "Benchmark",
    "Example",
    "ExampleScore",
    "ScoreReport",
    "BUILTIN_BENCHMARKS",
    "load_builtin_benchmark",
    "download_hydrosebench_data",
    "load_benchmark_from_file",
    "load_predictions_from_excel",
    "evaluate_all_models",
    "identify_model_columns",
    "sample_examples_by_category",
    "sample_benchmark_by_category",
    "save_benchmark",
    "create_summary_excel",
    "validate_data_quality",
    "generate_analysis_report",
]

