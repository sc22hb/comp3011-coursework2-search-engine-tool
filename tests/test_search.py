from pathlib import Path
import sys
import json

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

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
