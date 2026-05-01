"""Indexer implementation for the coursework search tool."""

from __future__ import annotations

import re
from typing import Iterable

from crawler import PageData


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)*")


def tokenise_text(text: str) -> list[str]:
    """Return case-insensitive tokens extracted from plain text."""
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


class Indexer:
    """Builds an inverted index from crawled page data."""

    def build_index(self, pages: Iterable[PageData]) -> dict[str, dict[str, dict[str, int | list[int]]]]:
        """Return an inverted index for the supplied pages."""
        index: dict[str, dict[str, dict[str, int | list[int]]]] = {}

        for page in pages:
            for position, token in enumerate(tokenise_text(page.text)):
                postings = index.setdefault(token, {})
                page_entry = postings.setdefault(
                    page.url,
                    {
                        "frequency": 0,
                        "positions": [],
                    },
                )
                page_entry["frequency"] += 1
                page_entry["positions"].append(position)

        return index
