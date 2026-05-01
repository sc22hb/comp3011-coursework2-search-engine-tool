from pathlib import Path
import json
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from crawler import PageData
import main as main_module
from main import SearchShell, build_index_with_defaults, main
from search import SearchEngine


def test_search_engine_defaults_to_empty_index() -> None:
    engine = SearchEngine()
    assert engine.index == {}


def test_search_engine_saves_and_loads_index_round_trip(tmp_path: Path) -> None:
    index = {
        "good": {
            "https://quotes.toscrape.com/": {
                "frequency": 2,
                "positions": [0, 2],
            }
        }
    }
    path = tmp_path / "index.json"

    saved_path = SearchEngine(index).save(path)
    loaded_engine = SearchEngine.load(saved_path)

    assert saved_path == path
    assert loaded_engine.index == index


def test_search_engine_load_raises_for_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.json"

    try:
        SearchEngine.load(missing_path)
    except FileNotFoundError as error:
        assert str(missing_path) in str(error)
    else:
        assert False, "Expected FileNotFoundError for a missing index file."


def test_search_engine_load_raises_for_invalid_json(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("{not-valid-json", encoding="utf-8")

    try:
        SearchEngine.load(invalid_path)
    except ValueError as error:
        assert str(invalid_path) in str(error)
    else:
        assert False, "Expected ValueError for an invalid JSON index file."


def test_search_engine_load_raises_for_non_mapping_json(tmp_path: Path) -> None:
    invalid_path = tmp_path / "list.json"
    invalid_path.write_text(json.dumps(["not", "an", "index"]), encoding="utf-8")

    try:
        SearchEngine.load(invalid_path)
    except ValueError as error:
        assert "valid inverted index" in str(error)
    else:
        assert False, "Expected ValueError for a non-mapping JSON index file."


def test_search_engine_print_word_is_case_insensitive() -> None:
    engine = SearchEngine(
        {
            "good": {
                "https://quotes.toscrape.com/": {
                    "frequency": 2,
                    "positions": [0, 2],
                }
            }
        }
    )

    assert engine.print_word("Good") == {
        "https://quotes.toscrape.com/": {
            "frequency": 2,
            "positions": [0, 2],
        }
    }


def test_search_engine_find_returns_intersection_ranked_by_frequency() -> None:
    engine = SearchEngine(
        {
            "good": {
                "https://quotes.toscrape.com/": {
                    "frequency": 3,
                    "positions": [0, 2, 4],
                },
                "https://quotes.toscrape.com/page/2/": {
                    "frequency": 1,
                    "positions": [0],
                },
            },
            "friends": {
                "https://quotes.toscrape.com/": {
                    "frequency": 1,
                    "positions": [1],
                },
                "https://quotes.toscrape.com/page/2/": {
                    "frequency": 4,
                    "positions": [1, 3, 5, 7],
                },
            },
        }
    )

    assert engine.find(["good", "friends"]) == [
        "https://quotes.toscrape.com/page/2/",
        "https://quotes.toscrape.com/",
    ]


def test_search_engine_find_supports_exact_phrase_queries() -> None:
    engine = SearchEngine(
        {
            "good": {
                "https://quotes.toscrape.com/": {
                    "frequency": 2,
                    "positions": [0, 4],
                },
                "https://quotes.toscrape.com/page/2/": {
                    "frequency": 1,
                    "positions": [0],
                },
            },
            "friends": {
                "https://quotes.toscrape.com/": {
                    "frequency": 1,
                    "positions": [1],
                },
                "https://quotes.toscrape.com/page/2/": {
                    "frequency": 1,
                    "positions": [3],
                },
            },
        }
    )

    assert engine.find(["good friends"]) == ["https://quotes.toscrape.com/"]


def test_search_engine_find_returns_empty_for_empty_query() -> None:
    engine = SearchEngine({"good": {}})
    assert engine.find([]) == []


def test_search_engine_suggests_close_query_terms() -> None:
    engine = SearchEngine(
        {
            "good": {
                "https://quotes.toscrape.com/": {
                    "frequency": 1,
                    "positions": [0],
                }
            },
            "friends": {
                "https://quotes.toscrape.com/": {
                    "frequency": 1,
                    "positions": [1],
                }
            },
        }
    )

    assert engine.suggest_query(["godo", "frends"]) == "good friends"


def test_search_engine_returns_no_suggestion_for_empty_query_terms() -> None:
    engine = SearchEngine({"good": {}})
    assert engine.suggest_query([]) is None


def test_search_engine_returns_no_suggestion_when_query_is_already_valid() -> None:
    engine = SearchEngine({"good": {"https://quotes.toscrape.com/": {"frequency": 1, "positions": [0]}}})
    assert engine.suggest_query(["good"]) is None


def test_search_engine_returns_no_suggestion_when_no_close_match_exists() -> None:
    engine = SearchEngine({"good": {"https://quotes.toscrape.com/": {"frequency": 1, "positions": [0]}}})
    assert engine.suggest_query(["xyzabc"]) is None


def test_search_engine_phrase_occurrences_supports_single_term_queries() -> None:
    engine = SearchEngine(
        {
            "good": {
                "https://quotes.toscrape.com/": {
                    "frequency": 1,
                    "positions": [0],
                }
            }
        }
    )

    assert engine._phrase_occurrences(["good"], "https://quotes.toscrape.com/") == 1


def test_search_engine_term_tfidf_returns_zero_for_missing_page() -> None:
    engine = SearchEngine(
        {
            "good": {
                "https://quotes.toscrape.com/": {
                    "frequency": 1,
                    "positions": [0],
                }
            }
        }
    )

    assert engine._term_tfidf("good", "https://quotes.toscrape.com/page/2/") == 0.0


class StubCrawler:
    def __init__(self, pages: list[PageData]) -> None:
        self.pages = pages

    def crawl(self) -> list[PageData]:
        return self.pages


class StubIndexer:
    def __init__(self, index: dict) -> None:
        self.index = index

    def build_index(self, pages: list[PageData]) -> dict:
        return self.index


def test_search_shell_build_saves_index_file(tmp_path: Path) -> None:
    pages = [
        PageData(
            url="https://quotes.toscrape.com/",
            title="Page 1",
            text="Good friends good books",
        )
    ]
    index = {
        "good": {
            "https://quotes.toscrape.com/": {
                "frequency": 2,
                "positions": [0, 2],
            }
        }
    }
    shell = SearchShell(
        crawler=StubCrawler(pages),
        indexer=StubIndexer(index),
        index_path=tmp_path / "index.json",
    )

    output = shell.run_command("build", [])

    assert "Built index for 1 pages with 1 unique terms." in output
    assert (tmp_path / "index.json").exists()


def test_search_shell_build_raises_when_no_pages_are_crawled(tmp_path: Path) -> None:
    shell = SearchShell(
        crawler=StubCrawler([]),
        indexer=StubIndexer({}),
        index_path=tmp_path / "index.json",
    )

    try:
        shell.run_command("build", [])
    except RuntimeError as error:
        assert "no pages were crawled" in str(error)
    else:
        assert False, "Expected RuntimeError when build crawls no pages."


def test_search_shell_load_reads_index_file(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    SearchEngine(
        {
            "good": {
                "https://quotes.toscrape.com/": {
                    "frequency": 1,
                    "positions": [0],
                }
            }
        }
    ).save(path)
    shell = SearchShell(index_path=path)

    output = shell.run_command("load", [])

    assert "Loaded index with 1 terms" in output
    assert shell.engine is not None


def test_search_shell_print_loads_saved_index_on_demand(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    SearchEngine(
        {
            "good": {
                "https://quotes.toscrape.com/": {
                    "frequency": 1,
                    "positions": [0],
                }
            }
        }
    ).save(path)
    shell = SearchShell(index_path=path)

    output = shell.run_command("print", ["Good"])

    assert json.loads(output) == {
        "https://quotes.toscrape.com/": {
            "frequency": 1,
            "positions": [0],
        }
    }


def test_search_shell_find_returns_matching_pages(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    SearchEngine(
        {
            "good": {
                "https://quotes.toscrape.com/": {
                    "frequency": 2,
                    "positions": [0, 2],
                }
            },
            "friends": {
                "https://quotes.toscrape.com/": {
                    "frequency": 1,
                    "positions": [1],
                }
            },
        }
    ).save(path)
    shell = SearchShell(index_path=path)

    output = shell.run_command("find", ["good", "friends"])

    assert output == "https://quotes.toscrape.com/"


def test_search_shell_find_returns_query_suggestion(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    SearchEngine(
        {
            "good": {
                "https://quotes.toscrape.com/": {
                    "frequency": 2,
                    "positions": [0, 2],
                }
            },
            "friends": {
                "https://quotes.toscrape.com/": {
                    "frequency": 1,
                    "positions": [1],
                }
            },
        }
    ).save(path)
    shell = SearchShell(index_path=path)

    output = shell.run_command("find", ["godo", "frends"])

    assert output == "No matching pages found.\nDid you mean: good friends?"


def test_search_shell_find_returns_plain_no_results_without_suggestion(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    SearchEngine(
        {
            "good": {
                "https://quotes.toscrape.com/": {
                    "frequency": 2,
                    "positions": [0, 2],
                }
            }
        }
    ).save(path)
    shell = SearchShell(index_path=path)

    output = shell.run_command("find", ["xyzabc"])

    assert output == "No matching pages found."


def test_search_shell_find_requires_query_terms(tmp_path: Path) -> None:
    shell = SearchShell(index_path=tmp_path / "index.json")

    try:
        shell.run_command("find", [])
    except ValueError as error:
        assert "requires at least one search term" in str(error)
    else:
        assert False, "Expected ValueError for an empty find command."


def test_main_returns_error_code_for_invalid_command(capsys) -> None:
    result = main(["unknown"])

    captured = capsys.readouterr()

    assert result == 1
    assert "Unknown command: unknown" in captured.err


def test_search_shell_print_requires_exactly_one_word(tmp_path: Path) -> None:
    shell = SearchShell(index_path=tmp_path / "index.json")

    try:
        shell.run_command("print", ["good", "friends"])
    except ValueError as error:
        assert "exactly one word" in str(error)
    else:
        assert False, "Expected ValueError for a multi-word print command."


def test_search_shell_run_command_line_rejects_empty_input(tmp_path: Path) -> None:
    shell = SearchShell(index_path=tmp_path / "index.json")

    try:
        shell.run_command_line("   ")
    except ValueError as error:
        assert "No command provided" in str(error)
    else:
        assert False, "Expected ValueError for an empty command line."


def test_search_shell_run_command_supports_quit(tmp_path: Path) -> None:
    shell = SearchShell(index_path=tmp_path / "index.json")

    try:
        shell.run_command("quit", [])
    except SystemExit as error:
        assert error.code == 0
    else:
        assert False, "Expected SystemExit for quit."


def test_build_index_with_defaults_uses_default_components(monkeypatch) -> None:
    pages = [PageData(url="u", title="t", text="Good friends")]
    expected_index = {"good": {"u": {"frequency": 1, "positions": [0]}}}

    class FakeCrawler:
        def crawl(self) -> list[PageData]:
            return pages

    class FakeIndexer:
        def build_index(self, crawled_pages: list[PageData]) -> dict:
            assert crawled_pages == pages
            return expected_index

    monkeypatch.setattr(main_module, "Crawler", FakeCrawler)
    monkeypatch.setattr(main_module, "Indexer", FakeIndexer)

    assert build_index_with_defaults() == expected_index


def test_main_returns_zero_for_successful_direct_command(monkeypatch, capsys) -> None:
    class FakeShell:
        def run_command(self, command: str, arguments: list[str]) -> str:
            assert command == "load"
            assert arguments == []
            return "loaded"

    monkeypatch.setattr(main_module, "SearchShell", lambda: FakeShell())

    result = main(["load"])

    captured = capsys.readouterr()
    assert result == 0
    assert captured.out.strip() == "loaded"


def test_main_returns_system_exit_code_for_direct_quit(monkeypatch) -> None:
    class FakeShell:
        def run_command(self, command: str, arguments: list[str]) -> str:
            raise SystemExit(3)

    monkeypatch.setattr(main_module, "SearchShell", lambda: FakeShell())

    assert main(["quit"]) == 3


def test_main_returns_zero_on_immediate_eof(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: (_ for _ in ()).throw(EOFError()))

    assert main([]) == 0


def test_main_interactive_loop_continues_after_value_error(monkeypatch, capsys) -> None:
    commands = iter(["   ", "bad", "load"])

    def fake_input(prompt: str) -> str:
        try:
            return next(commands)
        except StopIteration as error:
            raise EOFError() from error

    class FakeShell:
        def run_command_line(self, command_line: str) -> str:
            if command_line == "bad":
                raise ValueError("bad command")
            return "loaded"

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(main_module, "SearchShell", lambda: FakeShell())

    result = main([])

    captured = capsys.readouterr()
    assert result == 0
    assert "bad command" in captured.err
    assert "loaded" in captured.out


def test_main_interactive_loop_returns_system_exit_code(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: "quit")

    class FakeShell:
        def run_command_line(self, command_line: str) -> str:
            raise SystemExit(7)

    monkeypatch.setattr(main_module, "SearchShell", lambda: FakeShell())

    assert main([]) == 7


def test_committed_compiled_index_supports_real_queries() -> None:
    index_path = Path(__file__).resolve().parents[1] / "data" / "index.json"
    engine = SearchEngine.load(index_path)

    pages = sorted({url for postings in engine.index.values() for url in postings})

    assert len(engine.index) == 858
    assert len(pages) == 10
    assert pages[0] == "https://quotes.toscrape.com/"
    assert pages[-1] == "https://quotes.toscrape.com/page/9/"

    life_results = engine.find(["life"])
    assert len(life_results) == 10
    assert set(life_results) == set(pages)
    assert life_results[0] == "https://quotes.toscrape.com/page/2/"
    assert engine.find(["good friends"]) == ["https://quotes.toscrape.com/page/2/"]
    suggestion = engine.suggest_query(["godo", "frends"])
    assert suggestion is not None
    assert suggestion.endswith("friends")
