"""
Common utility functions for example code
"""

from pathlib import Path
import sys


def setup_package_path() -> Path:
    """
    Setup package path and return project root directory.
    
    Returns:
        Project root directory path
    """
    project_root = Path(__file__).resolve().parent.parent
    package_dir = project_root / "hydrosebench-eval"
    
    if package_dir.exists() and str(package_dir) not in sys.path:
        sys.path.insert(0, str(package_dir))
    
    return project_root


def get_output_dir(project_root: Path, example_name: str) -> Path:
    """
    Get output directory for an example.
    
    Args:
        project_root: Project root directory
        example_name: Example name (e.g., "example_1_basic_evaluation")
    
    Returns:
        Output directory path
    """
    output_dir = project_root / "examples" / "output" / example_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_test_data_path(project_root: Path) -> Path:
    """
    Get test data file path.
    Prioritizes CSV file, returns Excel file if CSV doesn't exist.
    
    Args:
        project_root: Project root directory
    
    Returns:
        Test data file path (CSV or Excel)
    """
    csv_path = project_root / "examples" / "test.csv"
    if csv_path.exists():
        return csv_path
    return project_root / "examples" / "test.xlsx"


def get_benchmark_data_path(project_root: Path) -> Path:
    """
    Get built-in benchmark data file path.
    Prioritizes CSV file, returns Excel file if CSV doesn't exist.
    
    Args:
        project_root: Project root directory
    
    Returns:
        Benchmark data file path (CSV or Excel)
    """
    csv_path = project_root / "hydrosebench-eval" / "hydrosebench" / "data" / "hydrosebench.csv"
    if csv_path.exists():
        return csv_path
    return project_root / "hydrosebench-eval" / "hydrosebench" / "data" / "hydrosebench.xlsx"
