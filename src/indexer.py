"""Indexer implementation for the coursework search tool."""

from __future__ import annotations

import re
from typing import Iterable, TypeAlias, TypedDict

from crawler import PageData


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)*")

# Standard English stop words excluded from the index to reduce noise and
# improve ranking precision.  The list is based on the classic information-
# retrieval stop list used by systems such as Lucene and NLTK.
STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "is", "it", "its", "this", "that",
    "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may",
    "might", "shall", "can", "not", "no", "nor", "so", "as", "up",
    "out", "about", "into", "over", "after", "before", "between", "under",
    "again", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "only", "own", "same", "than", "too", "very", "just",
    "because", "through", "during", "above", "below", "am", "i", "me",
    "my", "myself", "we", "our", "ours", "ourselves", "you", "your",
    "yours", "yourself", "yourselves", "he", "him", "his", "himself",
    "she", "her", "hers", "herself", "they", "them", "their", "theirs",
    "themselves", "what", "which", "who", "whom", "these", "those",
})


class PostingEntry(TypedDict):
    """Statistics stored for one term within one page."""

    frequency: int
    positions: list[int]


PostingsByPage: TypeAlias = dict[str, PostingEntry]
InvertedIndex: TypeAlias = dict[str, PostingsByPage]


def tokenise_text(text: str) -> list[str]:
    """Return case-insensitive tokens extracted from plain text."""
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def filter_stop_words(tokens: list[str]) -> list[str]:
    """Remove common stop words that add noise to the index."""
    return [token for token in tokens if token not in STOP_WORDS]


class Indexer:
    """Builds an inverted index from crawled page data."""

    def build_index(self, pages: Iterable[PageData]) -> InvertedIndex:
        """Return an inverted index for the supplied pages.

        Tokens are extracted, lowercased, and filtered through a stop-word
        list.  Each surviving token is recorded with its frequency and
        positional offsets within the page so that phrase queries can be
        resolved later.
        """
        index: InvertedIndex = {}

        for page in pages:
            tokens = filter_stop_words(tokenise_text(page.text))
            for position, token in enumerate(tokens):
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
