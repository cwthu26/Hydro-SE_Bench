from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence

from .scoring import ScoreReport, score_examples


@dataclass(slots=True, frozen=True)
class Example:
    """Represents a single question in the benchmark."""

    id: str
    input_text: str
    correct_options: tuple[str, ...]
    metadata: Mapping[str, object] = field(default_factory=dict)

    @property
    def is_multiple_choice(self) -> bool:
        return len(self.correct_options) > 1

    @property
    def category(self) -> str | None:
        return self.metadata.get("category")  # type: ignore[return-value]

    @property
    def level(self) -> str | None:
        return self.metadata.get("level")  # type: ignore[return-value]

    @property
    def question_type(self) -> str | None:
        return self.metadata.get("type")  # type: ignore[return-value]


class Benchmark:
    """Container for a full benchmark split."""

    def __init__(
        self,
        *,
        name: str,
        description: str | None,
        examples: Iterable[Example],
        source_path: Path | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self._examples: list[Example] = list(examples)
        if not self._examples:
            raise ValueError("benchmark must contain at least one example")
        self.source_path = source_path

    # --------------------------------------------------------------------- #
    # Constructors
    # --------------------------------------------------------------------- #
    @classmethod
    def from_file(cls, path: str | Path) -> "Benchmark":
        """Load a benchmark definition from a JSON file."""
        json_path = Path(path)
        with json_path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        return cls.from_dict(data, source_path=json_path)

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, object],
        *,
        source_path: Path | None = None,
    ) -> "Benchmark":
        """Construct a benchmark from the already-parsed JSON payload."""
        raw_examples = payload.get("examples")
        if not isinstance(raw_examples, Sequence):
            raise ValueError("payload['examples'] must be a list")

        name = str(payload.get("name") or "benchmark")
        description = payload.get("description")
        if description is not None:
            description = str(description)

        parsed_examples: list[Example] = []
        for idx, item in enumerate(raw_examples):
            if not isinstance(item, Mapping):
                raise ValueError("each example must be an object")
            target_scores = item.get("target_scores")
            if target_scores is None:
                target_scores = {}
            if not isinstance(target_scores, Mapping):
                raise ValueError("example target_scores must be an object")

            correct_letters = tuple(
                sorted(
                    letter
                    for letter, score in target_scores.items()
                    if isinstance(letter, str)
                    and len(letter) == 1
                    and letter.isalpha()
                    and score == 1
                )
            )

            # Support both "id" and "ID" field names
            example_id = (
                str(item.get("id") or item.get("ID"))
                if (item.get("id") or item.get("ID"))
                else f"{name}-{idx+1:04d}"
            )

            parsed_examples.append(
                Example(
                    id=example_id,
                    input_text=str(item.get("input", "")),
                    correct_options=correct_letters,
                    metadata={
                        key: item[key]
                        for key in ("category", "level", "type")
                        if key in item
                    },
                )
            )

        return cls(
            name=name,
            description=description,
            examples=parsed_examples,
            source_path=source_path,
        )

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @property
    def examples(self) -> Sequence[Example]:
        return self._examples

    def __iter__(self) -> Iterator[Example]:
        return iter(self._examples)

    def score(self, predictions: object) -> ScoreReport:
        """Score a set of predictions against this benchmark."""
        return score_examples(self._examples, predictions, benchmark_name=self.name)

