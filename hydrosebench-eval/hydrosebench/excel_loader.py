from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from .benchmark import Benchmark, Example


def _detect_file_format(file_path: Path) -> str:
    """
    Detect the actual file format (by reading file header).
    
    Args:
        file_path: File path
    
    Returns:
        'excel' if Excel format (.xlsx, .xls), 'csv' if CSV format, 'unknown' if cannot determine
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(8)  # Read first 8 bytes
            # Excel files (.xlsx) start with ZIP magic number: PK\x03\x04
            if header[:2] == b'PK':
                return 'excel'
            # Excel 97-2003 (.xls) starts with OLE2 format
            if header[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                return 'excel'
            # CSV files are usually text format, check if contains printable characters
            try:
                header.decode('utf-8', errors='strict')
                return 'csv'
            except UnicodeDecodeError:
                try:
                    header.decode('gbk', errors='strict')
                    return 'csv'
                except UnicodeDecodeError:
                    return 'unknown'
    except Exception:
        return 'unknown'


def _read_csv_safe(csv_path: Path) -> pd.DataFrame:
    """
    Safely read CSV file, trying multiple encodings and parameter combinations.
    
    Args:
        csv_path: CSV file path
    
    Returns:
        DataFrame object
    
    Raises:
        ValueError: If all attempts fail
    """
    # Check pandas version for compatibility with different parameters
    pandas_version = tuple(map(int, pd.__version__.split('.')[:2]))
    use_on_bad_lines = pandas_version >= (1, 3)  # pandas >= 1.3.0 supports on_bad_lines
    
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb18030", "latin-1"]
    last_error = None
    
    for encoding in encodings:
        try:
            # Try using Python engine for more lenient parsing
            read_csv_kwargs = {
                'filepath_or_buffer': csv_path,
                'encoding': encoding,
                'engine': 'python',
                'sep': ',',  # Explicitly specify separator
                'quotechar': '"',  # Explicitly specify quote character
            }
            if use_on_bad_lines:
                read_csv_kwargs['on_bad_lines'] = 'skip'
            else:
                read_csv_kwargs['error_bad_lines'] = False
                read_csv_kwargs['warn_bad_lines'] = False
            df = pd.read_csv(**read_csv_kwargs)
            return df
        except (UnicodeDecodeError, pd.errors.ParserError, TypeError) as e:
            last_error = e
            continue
    
    # If all encodings fail, try the most basic reading method (skip error lines)
    try:
        read_csv_kwargs = {
            'filepath_or_buffer': csv_path,
            'encoding': "utf-8",
            'engine': 'python',
            'sep': None,  # Auto-detect separator
        }
        if use_on_bad_lines:
            read_csv_kwargs['on_bad_lines'] = 'skip'
        else:
            read_csv_kwargs['error_bad_lines'] = False
            read_csv_kwargs['warn_bad_lines'] = False
        df = pd.read_csv(**read_csv_kwargs)
        return df
    except Exception as e:
        # Check if file is actually Excel format but misidentified as CSV
        actual_format = _detect_file_format(csv_path)
        if actual_format == 'excel':
            raise ValueError(
                f"Cannot read CSV file {csv_path}. "
                f"Detected file is actually Excel format (.xlsx or .xls), but extension is .csv. "
                f"Please rename the file to .xlsx or .xls, or use load_benchmark_from_file function (it auto-detects format)."
            ) from (last_error or e)
        raise ValueError(
            f"Cannot read CSV file {csv_path}. "
            f"Please check if file format is correct (ensure comma-separated, newlines in fields are quoted). "
            f"Error: {last_error or e}"
        ) from (last_error or e)


def load_benchmark_from_file(
    file_path: str | Path,
    *,
    answer_col: str = "Answer",
    question_col: str = "Question",
    id_col: str | None = "ID",
    category_col: str | None = "ID",
    level_col: str | None = "Level",
    type_col: str | None = "Type",
    sheet_name: str | int | None = 0,
) -> Benchmark:
    """
    Load benchmark from file (supports CSV, Excel formats).
    
    Supported file formats: .xlsx, .xls, .csv
    Function automatically detects file format, can correctly read even if extension doesn't match.

    Args:
        file_path: File path (supports CSV, XLSX, XLS formats)
        answer_col: Standard answer column name, defaults to "Answer"
        question_col: Question content column name, defaults to "Question"
        id_col: Question ID column name, if None then auto-generated
        category_col: Category column name (e.g., "ID"), used to extract category prefix (e.g., BK-001 -> BK)
        level_col: Difficulty level column name, defaults to "Level"
        type_col: Question type column name, defaults to "Type"
        sheet_name: Worksheet name or index (Excel files only), defaults to first worksheet

    Returns:
        Benchmark object

    Example:
        >>> benchmark = load_benchmark_from_file("hydrosebench.xlsx")
        >>> benchmark = load_benchmark_from_file("hydrosebench.csv")
        >>> benchmark = load_benchmark_from_file("hydrosebench.xls")
        >>> report = benchmark.score(predictions)
    """
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Select reading method based on file extension and actual format
    file_ext = file_path.suffix.lower()
    actual_format = _detect_file_format(file_path)
    
    # If extension is .csv but actual format is Excel, use Excel reading method
    if file_ext == ".csv" and actual_format == 'excel':
        print(f"⚠ Warning: File extension is .csv, but detected actual format is Excel. Will use Excel reading method.")
        df = pd.read_excel(file_path, sheet_name=sheet_name)
    elif file_ext == ".csv":
        df = _read_csv_safe(file_path)
    elif file_ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, sheet_name=sheet_name)
    else:
        # If extension is not supported but detected as Excel format, try using Excel reading
        if actual_format == 'excel':
            print(f"⚠ Warning: File extension is {file_ext}, but detected actual format is Excel. Will try using Excel reading method.")
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}. Supported formats: .csv, .xlsx, .xls")

    if question_col not in df.columns:
        raise ValueError(
            f"Column '{question_col}' not found in file. Available columns: {list(df.columns)}"
        )

    examples: list[Example] = []
    for idx, row in df.iterrows():
        answer_val = row.get(answer_col)
        answer_str = "" if pd.isna(answer_val) else str(answer_val).strip()

        question_text = str(row.get(question_col, "")).strip()

        # Parse option letters (extract A/B/C/D etc. from question text)
        option_letters = set(
            re.findall(r"([A-Z])\s*[\.．、：:）\)]", question_text)
        )
        if not option_letters:
            # If no options found in question, extract possible options from answer
            option_letters = set(ch for ch in answer_str if ch.isalpha() and ch.isupper())

        option_labels = sorted(option_letters) if option_letters else []

        # Parse correct answer (extract from Answer column)
        correct_letters: set[str] = set()
        for ch in answer_str:
            if ch.strip() and ch.isalpha() and ch.isupper():
                correct_letters.add(ch)
            elif ch in {",", "，", ";", "；", "/", "、", "+", "|"}:
                continue

        # If no option labels found, use letters from correct answer
        if not option_labels and correct_letters:
            option_labels = sorted(correct_letters)

        # Build metadata
        metadata: dict[str, Any] = {}

        if category_col and category_col in df.columns:
            category_val = row.get(category_col)
            if not pd.isna(category_val):
                category_str = str(category_val)
                match = re.search(r"[A-Za-z]+", category_str)
                if match:
                    metadata["category"] = match.group(0)

        if level_col and level_col in df.columns:
            level_val = row.get(level_col)
            if not pd.isna(level_val):
                level_str = str(level_val).strip()
                # Map common Chinese/English levels
                level_map = {
                    "A": "basic conceptual knowledge",
                    "B": "engineering applications",
                    "C": "reasoning and calculation",
                }
                metadata["level"] = level_map.get(level_str.upper(), level_str)

        if type_col and type_col in df.columns:
            type_val = row.get(type_col)
            if not pd.isna(type_val):
                type_str = str(type_val).strip()
                type_map = {
                    "单选题": "single choice",
                    "多选题": "multiple choice",
                    "single choice": "single choice",
                    "multiple choice": "multiple choice",
                    "single-choice": "single choice",
                    "multiple-choice": "multiple choice",
                }
                metadata["type"] = type_map.get(type_str, type_map.get(type_str.lower(), type_str))

        # Generate question ID
        if id_col and id_col in df.columns:
            example_id = str(row.get(id_col, "")).strip()
            if not example_id or pd.isna(row.get(id_col)):
                example_id = f"{file_path.stem}-{idx+1:04d}"
        else:
            example_id = f"{file_path.stem}-{idx+1:04d}"

        examples.append(
            Example(
                id=example_id,
                input_text=question_text,
                correct_options=tuple(sorted(correct_letters)),
                metadata=metadata,
            )
        )

    if not examples:
        raise ValueError(f"No valid examples found in file: {file_path}")

    file_type = "CSV" if file_ext == ".csv" else "Excel"
    return Benchmark(
        name=file_path.stem,
        description=f"Loaded from {file_type}: {file_path.name}",
        examples=examples,
        source_path=file_path,
    )


def load_predictions_from_excel(
    excel_path: str | Path,
    *,
    answer_col: str = "Answer",
    id_col: str | None = "ID",
    sheet_name: str | int | None = 0,
) -> dict[str, Any] | list[Any]:
    """
    Load model prediction results from Excel or CSV file.
    
    Supported file formats: .xlsx, .xls, .csv

    Supports two modes:
    1. If id_col is provided, returns dictionary {question_id: answer}
    2. Otherwise returns list, ordered by row

    Args:
        excel_path: Excel or CSV file path
        answer_col: Prediction answer column name, defaults to "Answer"
        id_col: Question ID column name. If provided, returns dictionary format; otherwise returns list format
        sheet_name: Worksheet name or index (Excel files only), defaults to first worksheet

    Returns:
        Prediction results, in dictionary or list format

    Example:
        >>> # Use ID column, returns dictionary
        >>> predictions = load_predictions_from_excel("model_output.xlsx", id_col="ID")
        >>> predictions = load_predictions_from_excel("model_output.csv", id_col="ID")
    >>> # Don't use ID column, returns list (ordered by row)
    >>> predictions = load_predictions_from_excel("model_output.xlsx", id_col=None)
    """
    excel_path = Path(excel_path)
    if not excel_path.is_file():
        raise FileNotFoundError(f"File not found: {excel_path}")

    # Select reading method based on file extension and actual format
    file_ext = excel_path.suffix.lower()
    actual_format = _detect_file_format(excel_path)
    
    # If extension is .csv but actual format is Excel, use Excel reading method
    if file_ext == ".csv" and actual_format == 'excel':
        print(f"⚠ Warning: File extension is .csv, but detected actual format is Excel. Will use Excel reading method.")
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    elif file_ext == ".csv":
        df = _read_csv_safe(excel_path)
    elif file_ext in (".xlsx", ".xls"):
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    else:
        # If extension is not supported but detected as Excel format, try using Excel reading
        if actual_format == 'excel':
            print(f"⚠ Warning: File extension is {file_ext}, but detected actual format is Excel. Will try using Excel reading method.")
            df = pd.read_excel(excel_path, sheet_name=sheet_name)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}. Supported formats: .csv, .xlsx, .xls")

    if answer_col not in df.columns:
        raise ValueError(
            f"Column '{answer_col}' not found in file. Available columns: {list(df.columns)}"
        )

    if id_col and id_col not in df.columns:
        raise ValueError(
            f"Column '{id_col}' not found in file. Available columns: {list(df.columns)}"
        )

    if id_col:
        # Return dictionary format {id: answer}
        result: dict[str, Any] = {}
        for _, row in df.iterrows():
            answer_val = row.get(answer_col)
            question_id_raw = row.get(id_col)
            if pd.isna(question_id_raw):
                continue
            question_id = str(question_id_raw).strip()
            if not question_id:
                continue
            if question_id in result:
                raise ValueError(f"Duplicate prediction ID: {question_id}")
            result[question_id] = None if pd.isna(answer_val) else answer_val
        return result
    else:
        # Return list format (ordered by row)
        result: list[Any] = []
        for _, row in df.iterrows():
            answer_val = row.get(answer_col)
            result.append(answer_val if not pd.isna(answer_val) else None)
        return result


