from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from crawler import PageData
from indexer import Indexer, tokenise_text


def test_indexer_class_exists() -> None:
    indexer = Indexer()
    assert isinstance(indexer, Indexer)


def test_tokenise_text_is_case_insensitive_and_preserves_apostrophes() -> None:
    tokens = tokenise_text("Don't STOP believing. Don't quit.")

    assert tokens == ["don't", "stop", "believing", "don't", "quit"]


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

    assert index["good"] == {
        "https://quotes.toscrape.com/": {
            "frequency": 2,
            "positions": [0, 2],
        },
        "https://quotes.toscrape.com/page/2/": {
            "frequency": 2,
            "positions": [0, 3],
        },
    }
    assert index["friends"] == {
        "https://quotes.toscrape.com/": {
            "frequency": 1,
            "positions": [1],
        }
    }


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
