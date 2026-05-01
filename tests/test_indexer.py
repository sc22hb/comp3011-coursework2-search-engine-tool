import pytest

from crawler import PageData
from indexer import STOP_WORDS, Indexer, filter_stop_words, tokenise_text


def test_indexer_class_exists() -> None:
    indexer = Indexer()
    assert isinstance(indexer, Indexer)


def test_tokenise_text_is_case_insensitive_and_preserves_apostrophes() -> None:
    tokens = tokenise_text("Don't STOP believing. Don't quit.")

    assert tokens == ["don't", "stop", "believing", "don't", "quit"]


def test_filter_stop_words_removes_common_words() -> None:
    tokens = ["the", "quick", "brown", "fox", "is", "a", "good", "animal"]
    filtered = filter_stop_words(tokens)

    assert filtered == ["quick", "brown", "fox", "good", "animal"]
    assert all(token not in STOP_WORDS for token in filtered)


def test_build_index_tracks_frequency_and_positions_per_page() -> None:
    pages = [
        PageData(
            url="https://quotes.toscrape.com/",
            title="Page 1",
            text="Good friends good books",
        ),
        PageData(
            url="https://quotes.toscrape.com/page/2/",
            title="Page 2",
            text="Good habits and good work",
        ),
    ]

    index = Indexer().build_index(pages)

    # "and" is a stop word so positions shift: good(0) habits(1) good(2) work(3)
    assert index["good"] == {
        "https://quotes.toscrape.com/": {
            "frequency": 2,
            "positions": [0, 2],
        },
        "https://quotes.toscrape.com/page/2/": {
            "frequency": 2,
            "positions": [0, 2],
        },
    }
    assert index["friends"] == {
        "https://quotes.toscrape.com/": {
            "frequency": 1,
            "positions": [1],
        }
    }
    assert "and" not in index


def test_build_index_ignores_empty_page_text() -> None:
    pages = [
        PageData(
            url="https://quotes.toscrape.com/",
            title="Empty Page",
            text="",
        )
    ]

    index = Indexer().build_index(pages)

    assert index == {}


@pytest.mark.parametrize(
    "text, expected",
    [
        ("", []),
        ("   ", []),
        ("hello", ["hello"]),
        ("HELLO", ["hello"]),
        ("it's", ["it's"]),
        ("one-two", ["one", "two"]),
        ("test123", ["test123"]),
        ("  spaces   everywhere  ", ["spaces", "everywhere"]),
    ],
    ids=[
        "empty-string",
        "whitespace-only",
        "single-word",
        "uppercase",
        "apostrophe",
        "hyphenated",
        "alphanumeric",
        "extra-spaces",
    ],
)
def test_tokenise_text_handles_edge_cases(text: str, expected: list[str]) -> None:
    assert tokenise_text(text) == expected


@pytest.mark.parametrize(
    "tokens, expected",
    [
        ([], []),
        (["the", "a", "is"], []),
        (["hello", "world"], ["hello", "world"]),
        (["the", "quick", "fox"], ["quick", "fox"]),
    ],
    ids=[
        "empty-list",
        "all-stop-words",
        "no-stop-words",
        "mixed",
    ],
)
def test_filter_stop_words_parametrised(tokens: list[str], expected: list[str]) -> None:
    assert filter_stop_words(tokens) == expected


def test_build_index_integration_multiple_pages() -> None:
    """Integration test: build an index from several pages and verify cross-page postings."""
    pages = [
        PageData(
            url="https://quotes.toscrape.com/",
            title="Page 1",
            text="Life beautiful wonderful life",
        ),
        PageData(
            url="https://quotes.toscrape.com/page/2/",
            title="Page 2",
            text="Beautiful day beautiful morning",
        ),
        PageData(
            url="https://quotes.toscrape.com/page/3/",
            title="Page 3",
            text="Wonderful morning wonderful evening",
        ),
    ]

    index = Indexer().build_index(pages)

    # "life" only appears on page 1
    assert set(index["life"]) == {"https://quotes.toscrape.com/"}
    assert index["life"]["https://quotes.toscrape.com/"]["frequency"] == 2

    # "beautiful" appears on pages 1 and 2
    assert set(index["beautiful"]) == {
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/2/",
    }

    # "wonderful" appears on pages 1 and 3
    assert set(index["wonderful"]) == {
        "https://quotes.toscrape.com/",
        "https://quotes.toscrape.com/page/3/",
    }

    # "morning" appears on pages 2 and 3
    assert set(index["morning"]) == {
        "https://quotes.toscrape.com/page/2/",
        "https://quotes.toscrape.com/page/3/",
    }
