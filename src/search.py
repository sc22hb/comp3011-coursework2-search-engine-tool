"""Search implementation for the coursework search tool."""

from __future__ import annotations

import json
from pathlib import Path


DEFAULT_INDEX_PATH = Path("data/index.json")


class SearchEngine:
    """Provides search operations over a loaded inverted index."""

    def __init__(self, index: dict | None = None) -> None:
        self.index = index or {}

    def save(self, path: str | Path = DEFAULT_INDEX_PATH) -> Path:
        """Persist the current index to disk."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.index, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return output_path

    @classmethod
    def load(cls, path: str | Path = DEFAULT_INDEX_PATH) -> "SearchEngine":
        """Load a persisted index from disk."""
        input_path = Path(path)
        try:
            raw_index = json.loads(input_path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise FileNotFoundError(f"Index file not found: {input_path}") from error
        except json.JSONDecodeError as error:
            raise ValueError(f"Index file is not valid JSON: {input_path}") from error

        if not isinstance(raw_index, dict):
            raise ValueError("Index file does not contain a valid inverted index.")

        return cls(index=raw_index)

    def print_word(self, word: str) -> dict:
        """Return the inverted-index entry for one word."""
        raise NotImplementedError("Search implementation is not complete yet.")

    def find(self, query_terms: list[str]) -> list[str]:
        """Return pages containing the supplied query terms."""
        raise NotImplementedError("Search implementation is not complete yet.")
