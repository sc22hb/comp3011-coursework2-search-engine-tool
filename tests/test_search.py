from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from search import SearchEngine


def test_search_engine_defaults_to_empty_index() -> None:
    engine = SearchEngine()
    assert engine.index == {}
