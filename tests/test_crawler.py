from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from crawler import Crawler


def test_crawler_class_exists() -> None:
    crawler = Crawler()
    assert isinstance(crawler, Crawler)
