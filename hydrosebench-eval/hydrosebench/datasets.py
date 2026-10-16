from __future__ import annotations

import shutil
from pathlib import Path

# Handle both relative import (when used as package) and absolute import (when run as script)
try:
    from .benchmark import Benchmark
except ImportError:
    # When running as script, use absolute import
    import sys
    parent_dir = Path(__file__).resolve().parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    from hydrosebench.benchmark import Benchmark

# Package data directory (relative to current file)
_PACKAGE_DIR = Path(__file__).resolve().parent
_DATA_DIR = _PACKAGE_DIR / "data"

BUILTIN_BENCHMARKS: dict[str, Path] = {
    "hydrosebench": _DATA_DIR / "hydrosebench.json",
    "hydrosebench_en": _DATA_DIR / "hydrosebench_en.json",
}


def load_builtin_benchmark(name: str) -> Benchmark:
    """
    Load a built-in benchmark dataset.
    
    Args:
        name: "hydrosebench" for Chinese or "hydrosebench_en" for English.
    
    Returns:
        Benchmark object
    
    Example:
        >>> benchmark = load_builtin_benchmark("hydrosebench")
        >>> report = benchmark.score(predictions)
    """
    try:
        json_path = BUILTIN_BENCHMARKS[name]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(
            f"Unknown benchmark '{name}'. Valid options: {sorted(BUILTIN_BENCHMARKS)}"
        ) from exc

    if not json_path.is_file():
        raise FileNotFoundError(
            f"Benchmark file not found: {json_path}. "
            "This may indicate a corrupted package installation."
        )
    return Benchmark.from_file(json_path)


def download_hydrosebench_data(
    file_format: str = "json", output_path: Path | str | None = None
) -> Path:
    """
    Download the built-in hydrosebench data file to the specified location.
    
    Args:
        file_format: File format, supports "json" or "csv", defaults to "json"
        output_path: Output file path. If None, saves to current working directory
    
    Returns:
        Path to the downloaded file
    
    Raises:
        ValueError: When file_format is not "json" or "csv"
        FileNotFoundError: When the built-in data file does not exist
    
    Example:
        >>> # Download JSON file to current directory
        >>> from hydrosebench import download_hydrosebench_data
        >>> path = download_hydrosebench_data("json")
        >>> print(f"File downloaded to: {path}")
        
        >>> # Download CSV file to specified path
        >>> from pathlib import Path
        >>> path = download_hydrosebench_data("csv", Path("./my_data/hydrosebench.csv"))
        >>> print(f"File downloaded to: {path}")
    """
    if file_format not in ("json", "csv"):
        raise ValueError(f'file_format must be "json" or "csv", got: {file_format}')
    
    # Determine source file path
    source_file = _DATA_DIR / f"hydrosebench.{file_format}"
    
    if not source_file.is_file():
        raise FileNotFoundError(
            f"Built-in data file not found: {source_file}. "
            "This may indicate a corrupted package installation."
        )
    
    # Determine output path
    if output_path is None:
        output_path = Path.cwd() / f"hydrosebench.{file_format}"
    else:
        output_path = Path(output_path)
        # If output path is a directory, add filename
        if output_path.is_dir():
            output_path = output_path / f"hydrosebench.{file_format}"
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy file
    shutil.copy2(source_file, output_path)
    
    return output_path


if __name__ == "__main__":
    # Test the functions
    print("Testing load_builtin_benchmark...")
    try:
        benchmark = load_builtin_benchmark("hydrosebench")
        print(f"✓ Successfully loaded benchmark with {len(benchmark.examples)} examples")
    except Exception as e:
        print(f"✗ Error loading benchmark: {e}")
    
    print("\nTesting download_hydrosebench_data...")
    try:
        json_path = download_hydrosebench_data("json", output_path=None)
        print(f"✓ Successfully downloaded to: {json_path}")
    except Exception as e:
        print(f"✗ Error downloading data: {e}")
