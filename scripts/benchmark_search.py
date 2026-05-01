"""Benchmark representative search queries against the compiled index."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import statistics
import sys
import time

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from search import SearchEngine


@dataclass(frozen=True)
class BenchmarkResult:
    """Stores timing statistics for one benchmark query."""

    query: str
    average_ms: float
    minimum_ms: float
    maximum_ms: float
    result_count: int


def benchmark_query(engine: SearchEngine, query: str, iterations: int) -> BenchmarkResult:
    """Measure one query over several iterations."""
    samples_ms: list[float] = []
    result_count = 0

    for _ in range(iterations):
        start = time.perf_counter()
        results = engine.find([query])
        elapsed_ms = (time.perf_counter() - start) * 1000
        samples_ms.append(elapsed_ms)
        result_count = len(results)

    return BenchmarkResult(
        query=query,
        average_ms=statistics.mean(samples_ms),
        minimum_ms=min(samples_ms),
        maximum_ms=max(samples_ms),
        result_count=result_count,
    )


def main() -> int:
    """Run representative benchmark queries against the saved index."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Number of times to execute each query.",
    )
    args = parser.parse_args()

    engine = SearchEngine.load()
    queries = [
        "life",
        "good friends",
        "be yourself",
        "truth",
        "happiness",
    ]

    results = [benchmark_query(engine, query, args.iterations) for query in queries]

    print("Query benchmark results")
    print("=======================")
    for result in results:
        print(
            f"{result.query!r}: avg={result.average_ms:.3f}ms "
            f"min={result.minimum_ms:.3f}ms max={result.maximum_ms:.3f}ms "
            f"results={result.result_count}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
