"""Utilities for sampling benchmark questions."""

from __future__ import annotations

import json
import re
import random
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Sequence

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore[assignment]

from .benchmark import Benchmark, Example

# Regular expression for extracting options from question text
_CHOICE_PATTERN = re.compile(r"([A-Z])\s*[\.．、：:）\)]")


def sample_examples_by_category(
    benchmark: Benchmark,
    per_category: int,
    *,
    categories: Sequence[str] | None = None,
    seed: int | None = None,
    allow_replacement: bool = False,
) -> list[Example]:
    """Randomly sample the same number of examples from each category.

    Args:
        benchmark: Source benchmark containing examples.
        per_category: Number of examples to sample from each category.
        categories: Optional subset of category names to sample from. If None,
            all categories present in the benchmark are used.
        seed: Optional seed for deterministic sampling.
        allow_replacement: If True, allows sampling with replacement when a
            category has fewer examples than requested. Defaults to False.

    Returns:
        A list of sampled Example objects.

    Raises:
        ValueError: If per_category <= 0, or a category has insufficient
            examples (when allow_replacement=False), or the category
            does not exist in the benchmark.
    """
    if per_category <= 0:
        raise ValueError("per_category must be a positive integer")

    rng = random.Random(seed)
    grouped: dict[str, list[Example]] = defaultdict(list)

    for example in benchmark.examples:
        category = getattr(example, "category", None) or example.metadata.get("category")
        if not category:
            category = "UNCATEGORIZED"
        grouped[str(category)].append(example)

    if categories is None:
        target_categories: Iterable[str] = sorted(grouped.keys())
    else:
        target_categories = categories

    sampled: list[Example] = []
    for category in target_categories:
        if category not in grouped:
            raise ValueError(f"Category '{category}' not found in benchmark")

        pool = grouped[category]
        if len(pool) < per_category and not allow_replacement:
            raise ValueError(
                f"Category '{category}' only has {len(pool)} examples, "
                f"cannot sample {per_category} without replacement."
            )

        if allow_replacement:
            sampled.extend(rng.choice(pool) for _ in range(per_category))
        else:
            sampled.extend(rng.sample(pool, per_category))

    return sampled


def sample_benchmark_by_category(
    benchmark: Benchmark,
    per_category: int,
    *,
    categories: Sequence[str] | None = None,
    seed: int | None = None,
    allow_replacement: bool = False,
    name_suffix: str = "sampled",
    output_path: str | Path | None = None,
) -> Benchmark:
    """
    Create a new Benchmark containing samples from each category.
    
    Args:
        benchmark: Source benchmark to sample from
        per_category: Number of examples to sample from each category
        categories: Optional subset of category names to sample from
        seed: Optional seed for deterministic sampling
        allow_replacement: If True, allows sampling with replacement
        name_suffix: Suffix to add to benchmark name
        output_path: Optional path to save the sampled benchmark. 
                     Format is auto-detected based on input format or file extension.
    
    Returns:
        A new Benchmark containing sampled examples
    """
    sampled_examples = sample_examples_by_category(
        benchmark,
        per_category,
        categories=categories,
        seed=seed,
        allow_replacement=allow_replacement,
    )

    new_name = f"{benchmark.name}_{name_suffix}" if name_suffix else benchmark.name
    new_description = (
        f"{benchmark.description or benchmark.name} "
        f"(sampled {per_category} per category)"
    )

    sampled_benchmark = Benchmark(
        name=new_name,
        description=new_description,
        examples=sampled_examples,
        source_path=benchmark.source_path,
    )
    
    # If output path is provided, automatically save
    if output_path:
        save_benchmark(sampled_benchmark, output_path)
    
    return sampled_benchmark


def save_benchmark(
    benchmark: Benchmark,
    output_path: str | Path,
    *,
    format: str | None = None,
) -> Path:
    """
    Save Benchmark to file, automatically select output format based on input format or specified format.
    
    Args:
        benchmark: Benchmark object to save
        output_path: Output file path
        format: Output format ("csv", "excel", "json", or None for auto-detection)
    
    Returns:
        Output file path
    
    Raises:
        ValueError: If format is not supported or cannot be determined
        ImportError: If pandas is required for CSV/Excel but not installed
    """
    output_path = Path(output_path)
    
    # Determine output format
    if format is None:
        # Judge based on benchmark's source_path
        if benchmark.source_path:
            source_ext = benchmark.source_path.suffix.lower()
            if source_ext == ".csv":
                format = "csv"
            elif source_ext in (".xlsx", ".xls", ".excel"):
                format = "excel"
            elif source_ext == ".json":
                format = "json"
            else:
                # Judge based on output path extension
                output_ext = output_path.suffix.lower()
                if output_ext == ".csv":
                    format = "csv"
                elif output_ext in (".xlsx", ".xls", ".excel"):
                    format = "excel"
                elif output_ext == ".json":
                    format = "json"
                else:
                    # Default to CSV (lighter weight)
                    format = "csv"
        else:
            # Judge based on output path extension
            output_ext = output_path.suffix.lower()
            if output_ext == ".csv":
                format = "csv"
            elif output_ext in (".xlsx", ".xls", ".excel"):
                format = "excel"
            elif output_ext == ".json":
                format = "json"
            else:
                # Default to CSV (lighter weight)
                format = "csv"
    
    format = format.lower()
    
    if format == "json":
        # Save as JSON, format consistent with original JSON file
        examples_data = []
        for ex in benchmark.examples:
            # Extract all options (A, B, C, D, etc.) from question text
            option_letters = set(_CHOICE_PATTERN.findall(ex.input_text))
            
            # If no options found, use letters from correct answer
            if not option_letters:
                option_letters = set(ex.correct_options)
            
            # Build target_scores, including all options
            target_scores = {}
            for option in sorted(option_letters):
                target_scores[option] = 1 if option in ex.correct_options else 0
            
            # Build example data, use "ID" field (consistent with original format)
            example_data = {
                "input": ex.input_text,
                "target_scores": target_scores,
                "ID": ex.id,  # Use "ID" instead of "id"
            }
            
            # Add category, level, type from metadata
            if ex.category:
                example_data["category"] = ex.category
            if ex.level:
                example_data["level"] = ex.level
            if ex.question_type:
                example_data["type"] = ex.question_type
            
            examples_data.append(example_data)
        
        data = {
            "name": benchmark.name,
            "description": benchmark.description,
            "examples": examples_data,
        }
        
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        return output_path
    
    elif format == "csv":
        # Save as CSV
        if pd is None:
            raise ImportError(
                "pandas is required for CSV export. Install it with: pip install pandas"
            )
        
        rows = []
        for ex in benchmark.examples:
            rows.append({
                "ID": ex.id,
                "Question": ex.input_text,
                "Answer": ",".join(sorted(ex.correct_options)),
                "Category": ex.category or "",
                "Level": ex.level or "",
                "Type": ex.question_type or "",
            })
        
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")  # Use utf-8-sig for Excel to open correctly
        return output_path
    
    elif format == "excel":
        # Save as Excel
        if pd is None:
            raise ImportError(
                "pandas is required for Excel export. Install it with: pip install pandas openpyxl"
            )
        
        rows = []
        for ex in benchmark.examples:
            rows.append({
                "ID": ex.id,
                "Question": ex.input_text,
                "Answer": ",".join(sorted(ex.correct_options)),
                "Category": ex.category or "",
                "Level": ex.level or "",
                "Type": ex.question_type or "",
            })
        
        df = pd.DataFrame(rows)
        
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Benchmark", index=False)
            
            # Set column widths
            worksheet = writer.sheets["Benchmark"]
            worksheet.column_dimensions["A"].width = 15  # ID
            worksheet.column_dimensions["B"].width = 50  # Question
            worksheet.column_dimensions["C"].width = 15  # Answer
            worksheet.column_dimensions["D"].width = 15  # Category
            worksheet.column_dimensions["E"].width = 12  # Level
            worksheet.column_dimensions["F"].width = 12  # Type
        
        return output_path
    
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'csv', 'excel' or 'json'.")

