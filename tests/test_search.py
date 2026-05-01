from pathlib import Path
import json
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from crawler import PageData
from main import SearchShell, main
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
