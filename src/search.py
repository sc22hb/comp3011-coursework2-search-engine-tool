"""Search implementation for the coursework search tool."""


class SearchEngine:
    """Provides search operations over a loaded inverted index."""

    def __init__(self, index: dict | None = None) -> None:
        self.index = index or {}

    def print_word(self, word: str) -> dict:
        """Return the inverted-index entry for one word."""
        raise NotImplementedError("Search implementation is not complete yet.")

    def find(self, query_terms: list[str]) -> list[str]:
        """Return pages containing the supplied query terms."""
        raise NotImplementedError("Search implementation is not complete yet.")
