from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from indexer import Indexer


def test_indexer_class_exists() -> None:
    indexer = Indexer()
    assert isinstance(indexer, Indexer)
