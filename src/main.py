"""Command-line entry point for the coursework search tool."""

from __future__ import annotations

import json
from pathlib import Path
import shlex
import sys

from crawler import Crawler
from indexer import Indexer, InvertedIndex
from search import DEFAULT_INDEX_PATH, SearchEngine

INTERACTIVE_BANNER = "Search Engine Tool"
INTERACTIVE_COMMANDS = "Commands: build | load | print <term> | find <query> | exit"


class SearchShell:
    """Provides the coursework command shell operations."""

    def __init__(
        self,
        crawler: Crawler | None = None,
        indexer: Indexer | None = None,
        index_path: str | Path = DEFAULT_INDEX_PATH,
    ) -> None:
        self.crawler = crawler or Crawler()
        self.indexer = indexer or Indexer()
        self.index_path = Path(index_path)
        self.engine: SearchEngine | None = None

    def run_command(self, command: str, arguments: list[str]) -> str:
        """Execute one command and return the user-facing output."""
        if command == "build":
            return self._build_index()
        if command == "load":
            return self._load_index()
        if command == "print":
            return self._print_word(arguments)
        if command == "find":
            return self._find_query(arguments)
        if command in {"exit", "quit"}:
            raise SystemExit(0)

        raise ValueError(f"Unknown command: {command}")

    def run_command_line(self, command_line: str) -> str:
        """Parse and execute a command line entered by the user."""
        parts = shlex.split(command_line)
        if not parts:
            raise ValueError("No command provided.")

        return self.run_command(parts[0], parts[1:])

    def _build_index(self) -> str:
        """Crawl the target site, build the index, and persist it to disk."""
        pages = self.crawler.crawl()
        if not pages:
            raise RuntimeError("Build failed because no pages were crawled.")

        index = self.indexer.build_index(pages)
        page_texts = {page.url: page.text for page in pages}
        self.engine = SearchEngine(index, page_texts=page_texts)
        output_path = self.engine.save(self.index_path)
        return (
            f"Built index for {len(pages)} pages with {len(index)} unique terms. "
            f"Saved to {output_path}."
        )

    def _load_index(self) -> str:
        """Load a previously saved index from disk."""
        self.engine = SearchEngine.load(self.index_path)
        return f"Loaded index with {len(self.engine.index)} terms from {self.index_path}."

    def _print_word(self, arguments: list[str]) -> str:
        """Return the JSON-formatted inverted-index entry for a single word."""
        if len(arguments) != 1:
            raise ValueError("The print command requires exactly one word.")

        entry = self._require_engine().print_word(arguments[0])
        return json.dumps(entry, indent=2, sort_keys=True)

    def _find_query(self, arguments: list[str]) -> str:
        """Search the index for the given terms and return ranked results with snippets."""
        if not arguments:
            raise ValueError("The find command requires at least one search term.")

        engine = self._require_engine()
        results = engine.find(arguments)
        if not results:
            suggestion = engine.suggest_query(arguments)
            if suggestion is not None:
                return f"No matching pages found.\nDid you mean: {suggestion}?"

            return "No matching pages found."

        lines: list[str] = []
        for url in results:
            lines.append(url)
            excerpt = engine.snippet(url, arguments)
            if excerpt:
                lines.append(f"  {excerpt}")

        return "\n".join(lines)

    def _require_engine(self) -> SearchEngine:
        """Return the active engine, auto-loading from disk if needed."""
        if self.engine is None:
            self.engine = SearchEngine.load(self.index_path)

        return self.engine


def build_index_with_defaults() -> InvertedIndex:
    """Build an index using the default crawler and indexer."""
    pages = Crawler().crawl()
    return Indexer().build_index(pages)


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""
    args = list(sys.argv[1:] if argv is None else argv)
    shell = SearchShell()

    if args:
        try:
            output = shell.run_command(args[0], args[1:])
        except (FileNotFoundError, RuntimeError, SystemExit, ValueError) as error:
            if isinstance(error, SystemExit):
                return error.code

            print(str(error), file=sys.stderr)
            return 1

        print(output)
        return 0

    print(INTERACTIVE_BANNER)
    print(INTERACTIVE_COMMANDS)

    while True:
        try:
            command_line = input("> ")
        except EOFError:
            return 0

        if not command_line.strip():
            continue

        try:
            output = shell.run_command_line(command_line)
        except SystemExit as error:
            return error.code
        except (FileNotFoundError, RuntimeError, ValueError) as error:
            print(str(error), file=sys.stderr)
            continue

        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
