"""Indexer implementation for the coursework search tool."""

from __future__ import annotations

import re
from typing import Iterable, TypeAlias, TypedDict

from crawler import PageData


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)*")


class PostingEntry(TypedDict):
    """Statistics stored for one term within one page."""

    frequency: int
    positions: list[int]


PostingsByPage: TypeAlias = dict[str, PostingEntry]
InvertedIndex: TypeAlias = dict[str, PostingsByPage]


def tokenise_text(text: str) -> list[str]:
    """Return case-insensitive tokens extracted from plain text."""
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


class Indexer:
    """Builds an inverted index from crawled page data."""

    def build_index(self, pages: Iterable[PageData]) -> InvertedIndex:
        """Return an inverted index for the supplied pages."""
        index: InvertedIndex = {}

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
