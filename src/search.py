"""Search implementation for the coursework search tool."""

from __future__ import annotations

from difflib import get_close_matches
import json
import math
from pathlib import Path

from indexer import InvertedIndex, PostingEntry, tokenise_text

DEFAULT_INDEX_PATH = Path("data/index.json")


class SearchEngine:
    """Provides search operations over a loaded inverted index."""

    def __init__(self, index: InvertedIndex | None = None) -> None:
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

    def print_word(self, word: str) -> dict[str, PostingEntry]:
        """Return the inverted-index entry for one word."""
        tokens = tokenise_text(word)
        if len(tokens) != 1:
            return {}

        return self.index.get(tokens[0], {})

    def find(self, query_terms: list[str]) -> list[str]:
        """Return pages containing the supplied query terms."""
        components = self._parse_query_components(query_terms)
        if not components:
            return []

        matching_urls: set[str] | None = None
        for component in components:
            component_matches = self._matching_pages_for_component(component)
            if not component_matches:
                return []

            if matching_urls is None:
                matching_urls = component_matches
            else:
                matching_urls &= component_matches

        if not matching_urls:
            return []

        ranked_urls = sorted(
            matching_urls,
            key=lambda url: (
                -self._query_score(components, url),
                url,
            ),
        )
        return ranked_urls

    def suggest_query(self, query_terms: list[str]) -> str | None:
        """Return a suggested alternative query when terms are close to index terms."""
        components = self._parse_query_components(query_terms)
        if not components:
            return None

        suggested_components: list[str] = []
        changed = False
        vocabulary = sorted(self.index)

        for component in components:
            suggested_tokens: list[str] = []
            for token in component:
                if token in self.index:
                    suggested_tokens.append(token)
                    continue

                matches = get_close_matches(token, vocabulary, n=1, cutoff=0.75)
                if not matches:
                    return None

                suggested_tokens.append(matches[0])
                changed = True

            suggested_components.append(" ".join(suggested_tokens))

        if not changed:
            return None

        return " ".join(suggested_components)

    def _parse_query_components(self, query_terms: list[str]) -> list[list[str]]:
        components: list[list[str]] = []

        for term in query_terms:
            tokens = tokenise_text(term)
            if tokens:
                components.append(tokens)

        return components

    def _matching_pages_for_component(self, component: list[str]) -> set[str]:
        if len(component) == 1:
            return set(self.index.get(component[0], {}))

        candidate_pages: set[str] | None = None
        for token in dict.fromkeys(component):
            postings = self.index.get(token, {})
            if not postings:
                return set()

            if candidate_pages is None:
                candidate_pages = set(postings)
            else:
                candidate_pages &= set(postings)

        if not candidate_pages:
            return set()

        matching_pages = {
            url for url in candidate_pages if self._phrase_occurrences(component, url) > 0
        }
        return matching_pages

    def _phrase_occurrences(self, component: list[str], url: str) -> int:
        if len(component) == 1:
            return 1 if url in self.index.get(component[0], {}) else 0

        position_sets = [
            set(self.index[token][url]["positions"])
            for token in component
            if url in self.index.get(token, {})
        ]

        if len(position_sets) != len(component):
            return 0

        occurrences = 0
        for start_position in position_sets[0]:
            if all(
                (start_position + offset) in position_sets[offset]
                for offset in range(1, len(component))
            ):
                occurrences += 1

        return occurrences

    def _query_score(self, components: list[list[str]], url: str) -> float:
        score = 0.0

        for component in components:
            unique_tokens = list(dict.fromkeys(component))
            component_score = sum(self._term_tfidf(token, url) for token in unique_tokens)
            if len(component) > 1:
                component_score += 0.5 * self._phrase_occurrences(component, url)
            score += component_score

        return score

    def _term_tfidf(self, term: str, url: str) -> float:
        postings = self.index.get(term, {})
        posting = postings.get(url)
        if posting is None:
            return 0.0

        term_frequency = posting["frequency"]
        document_frequency = len(postings)
        document_count = self._document_count()
        inverse_document_frequency = math.log((1 + document_count) / (1 + document_frequency)) + 1
        return (1 + math.log(term_frequency)) * inverse_document_frequency

    def _document_count(self) -> int:
        documents: set[str] = set()
        for postings in self.index.values():
            documents.update(postings)

        return len(documents)
