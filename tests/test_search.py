from pathlib import Path
import json

import pytest

from crawler import PageData
from indexer import Indexer
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


def test_search_engine_ranked_results_include_scores() -> None:
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

    results = engine.ranked_results(["good", "friends"])

    assert [url for url, _score in results] == [
        "https://quotes.toscrape.com/page/2/",
        "https://quotes.toscrape.com/",
    ]
    assert results[0][1] > results[1][1]


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


def test_search_engine_phrase_query_does_not_match_across_stop_words() -> None:
    engine = SearchEngine(
        {
            "good": {
                "https://quotes.toscrape.com/": {
                    "frequency": 1,
                    "positions": [0],
                },
            },
            "and": {
                "https://quotes.toscrape.com/": {
                    "frequency": 1,
                    "positions": [1],
                },
            },
            "friends": {
                "https://quotes.toscrape.com/": {
                    "frequency": 1,
                    "positions": [2],
                },
            },
        },
        page_texts={"https://quotes.toscrape.com/": "good and friends"},
    )

    assert engine.find(["good friends"]) == []


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


def test_search_shell_build_reports_progress_updates(tmp_path: Path) -> None:
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
    progress_messages: list[str] = []
    shell = SearchShell(
        crawler=StubCrawler(pages),
        indexer=StubIndexer(index),
        index_path=tmp_path / "index.json",
        progress_callback=progress_messages.append,
    )

    shell.run_command("build", [])

    assert progress_messages == [
        "Starting crawl of the target site...",
        "Crawled 1 pages. Building inverted index...",
        f"Built 1 unique terms. Saving index to {tmp_path / 'index.json'}...",
    ]


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

    assert output.startswith("https://quotes.toscrape.com/  [score: ")


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


def test_main_interactive_loop_prints_banner(monkeypatch, capsys) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: (_ for _ in ()).throw(EOFError()))

    result = main([])

    captured = capsys.readouterr()
    assert result == 0
    assert "Search Engine Tool" in captured.out
    assert "Commands: build | load | print <term> | find <query> | exit" in captured.out


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
    assert "Search Engine Tool" in captured.out
    assert "bad command" in captured.err
    assert "loaded" in captured.out


def test_main_interactive_loop_returns_system_exit_code(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda prompt: "quit")

    class FakeShell:
        def run_command_line(self, command_line: str) -> str:
            raise SystemExit(7)

    monkeypatch.setattr(main_module, "SearchShell", lambda: FakeShell())

    assert main([]) == 7


def test_search_engine_saves_and_loads_page_texts_round_trip(tmp_path: Path) -> None:
    index = {
        "good": {
            "https://quotes.toscrape.com/": {
                "frequency": 1,
                "positions": [0],
            }
        }
    }
    page_texts = {"https://quotes.toscrape.com/": "Good friends good books"}
    path = tmp_path / "index.json"

    SearchEngine(index, page_texts=page_texts).save(path)
    loaded = SearchEngine.load(path)

    assert loaded.index == index
    assert loaded.page_texts == page_texts


def test_search_engine_load_supports_legacy_bare_index(tmp_path: Path) -> None:
    """Verify that a plain dict (without the page_texts wrapper) still loads."""
    bare_index = {
        "good": {
            "https://quotes.toscrape.com/": {
                "frequency": 1,
                "positions": [0],
            }
        }
    }
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(bare_index), encoding="utf-8")

    loaded = SearchEngine.load(path)

    assert loaded.index == bare_index
    assert loaded.page_texts == {}


def test_search_engine_snippet_returns_context_around_match() -> None:
    index = {
        "life": {
            "https://quotes.toscrape.com/": {
                "frequency": 1,
                "positions": [2],
            }
        }
    }
    page_texts = {
        "https://quotes.toscrape.com/": "enjoy your life every single day",
    }
    engine = SearchEngine(index, page_texts=page_texts)

    result = engine.snippet("https://quotes.toscrape.com/", ["life"])

    assert result is not None
    assert "life" in result


def test_search_engine_snippet_uses_true_phrase_start_position() -> None:
    index = {
        "good": {
            "https://quotes.toscrape.com/": {
                "frequency": 2,
                "positions": [0, 10],
            }
        },
        "friends": {
            "https://quotes.toscrape.com/": {
                "frequency": 1,
                "positions": [11],
            }
        },
    }
    page_texts = {
        "https://quotes.toscrape.com/": "good ideas matter every day for thoughtful readers and curious minds good friends stay close",
    }
    engine = SearchEngine(index, page_texts=page_texts)

    result = engine.snippet("https://quotes.toscrape.com/", ["good friends"])

    assert result is not None
    assert "good friends stay close" in result
    assert "good ideas matter" not in result


def test_search_engine_snippet_returns_none_without_page_texts() -> None:
    engine = SearchEngine(
        {"good": {"u": {"frequency": 1, "positions": [0]}}}
    )

    assert engine.snippet("u", ["good"]) is None


@pytest.mark.parametrize(
    "query, expected_urls",
    [
        (["good"], ["https://quotes.toscrape.com/", "https://quotes.toscrape.com/page/2/"]),
        (["friends"], ["https://quotes.toscrape.com/"]),
        (["nonexistent"], []),
        ([], []),
    ],
    ids=["single-common-term", "single-rare-term", "missing-term", "empty-query"],
)
def test_search_engine_find_parametrised(query: list[str], expected_urls: list[str]) -> None:
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
            },
        }
    )

    results = engine.find(query)

    assert set(results) == set(expected_urls)


@pytest.mark.parametrize(
    "word, expected_empty",
    [
        ("good", False),
        ("GOOD", False),
        ("nonexistent", True),
        ("good friends", True),
    ],
    ids=["lowercase", "uppercase", "missing", "multi-word-rejected"],
)
def test_search_engine_print_word_parametrised(word: str, expected_empty: bool) -> None:
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

    result = engine.print_word(word)

    assert (result == {}) == expected_empty


def test_integration_crawl_index_search_pipeline() -> None:
    """Integration test: exercise the full crawl -> index -> search pipeline with stubs."""
    pages = [
        PageData(
            url="https://quotes.toscrape.com/",
            title="Page 1",
            text="Life beautiful wonderful life quotes",
        ),
        PageData(
            url="https://quotes.toscrape.com/page/2/",
            title="Page 2",
            text="Beautiful morning quotes life goes on",
        ),
    ]

    indexer = Indexer()
    index = indexer.build_index(pages)
    page_texts = {p.url: p.text for p in pages}
    engine = SearchEngine(index, page_texts=page_texts)

    # "life" appears in both pages
    life_results = engine.find(["life"])
    assert set(life_results) == {
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/2/",
    }

    # "wonderful" only in page 1
    assert engine.find(["wonderful"]) == ["https://quotes.toscrape.com/"]

    # AND query: "life" AND "morning" — only page 2 has both
    assert engine.find(["life", "morning"]) == ["https://quotes.toscrape.com/page/2/"]

    # Snippet works
    snippet = engine.snippet("https://quotes.toscrape.com/", ["life"])
    assert snippet is not None
    assert "life" in snippet

    # Print returns expected postings
    life_postings = engine.print_word("life")
    assert "https://quotes.toscrape.com/" in life_postings
    assert "https://quotes.toscrape.com/page/2/" in life_postings

    # Query suggestion
    suggestion = engine.suggest_query(["lif"])
    assert suggestion == "life"


def test_search_engine_snippet_with_phrase_query() -> None:
    """Cover the multi-token branch in snippet (lines 156-163)."""
    index = {
        "good": {
            "u": {"frequency": 1, "positions": [0]},
        },
        "friends": {
            "u": {"frequency": 1, "positions": [1]},
        },
    }
    page_texts = {"u": "good friends are rare treasures in life keep them close always"}
    engine = SearchEngine(index, page_texts=page_texts)

    result = engine.snippet("u", ["good friends"])

    assert result is not None
    assert "good" in result
    assert "friends" in result


def test_search_engine_snippet_adds_ellipsis_for_long_page() -> None:
    """Cover the ellipsis branches (lines 171-174)."""
    words = " ".join(f"word{i}" for i in range(30))
    index = {
        "word15": {
            "u": {"frequency": 1, "positions": [15]},
        },
    }
    page_texts = {"u": words}
    engine = SearchEngine(index, page_texts=page_texts)

    result = engine.snippet("u", ["word15"])

    assert result is not None
    assert result.startswith("...")
    assert result.endswith("...")


def test_search_engine_find_returns_empty_when_intersection_is_empty() -> None:
    """Cover line 88 — components each match pages but their intersection is empty."""
    engine = SearchEngine(
        {
            "alpha": {
                "https://quotes.toscrape.com/": {
                    "frequency": 1,
                    "positions": [0],
                },
            },
            "beta": {
                "https://quotes.toscrape.com/page/2/": {
                    "frequency": 1,
                    "positions": [0],
                },
            },
        }
    )

    assert engine.find(["alpha", "beta"]) == []


def test_search_engine_snippet_returns_none_for_empty_components() -> None:
    """Cover line 144 — query that produces no components after tokenisation."""
    engine = SearchEngine(
        {"good": {"u": {"frequency": 1, "positions": [0]}}},
        page_texts={"u": "good text"},
    )

    assert engine.snippet("u", []) is None


def test_search_engine_snippet_returns_none_when_term_not_in_index() -> None:
    """Cover line 165-166 — no matching position found."""
    engine = SearchEngine(
        {"good": {"u": {"frequency": 1, "positions": [0]}}},
        page_texts={"u": "good text"},
    )

    assert engine.snippet("u", ["missing"]) is None


def test_committed_compiled_index_supports_real_queries() -> None:
    index_path = Path(__file__).resolve().parents[1] / "data" / "index.json"
    engine = SearchEngine.load(index_path)

    pages = sorted({url for postings in engine.index.values() for url in postings})

    assert len(pages) == 212
    assert pages[0] == "https://quotes.toscrape.com/"
    assert "https://quotes.toscrape.com/page/10/" in pages
    assert "https://quotes.toscrape.com/author/Albert-Einstein/" in pages
    assert "https://quotes.toscrape.com/tag/friends/" in pages

    # The compiled artifact should support results from quote, tag, and author pages.
    friends_results = engine.find(["friends"])
    assert friends_results[:3] == [
        "https://quotes.toscrape.com/tag/friends/",
        "https://quotes.toscrape.com/tag/friends/page/1/",
        "https://quotes.toscrape.com/page/2/",
    ]

    phrase_results = engine.find(["good friends"])
    assert phrase_results[:3] == [
        "https://quotes.toscrape.com/tag/friends/",
        "https://quotes.toscrape.com/tag/friends/page/1/",
        "https://quotes.toscrape.com/page/2/",
    ]

    # Common stop words remain searchable because the positional index is complete.
    for stop_word in ("the", "is", "a", "and", "of"):
        assert stop_word in engine.index

    suggestion = engine.suggest_query(["godo", "frends"])
    assert suggestion is not None
    assert suggestion.endswith("friends")
