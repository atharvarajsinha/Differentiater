"""Benchmark Differentiater on synthetic files of increasing size.

Usage::

    python benchmarks/benchmark.py            # 100 .. 100,000 lines
    python benchmarks/benchmark.py 1000 5000  # custom sizes

Each "file B" is "file A" with roughly 1% of its lines modified, 0.5%
inserted and 0.5% deleted, which resembles a typical code change.
"""

from __future__ import annotations

import random
import sys
import time
from typing import List, Tuple

from differentiater.engine import compare_documents
from differentiater.models.document import LoadedDocument

DEFAULT_SIZES = [100, 1_000, 10_000, 100_000]


def make_pair(size: int, seed: int = 42) -> Tuple[List[str], List[str]]:
    rng = random.Random(seed)
    old = [f"    value_{i} = compute(item_{i % 97}, factor={i % 13})" for i in range(size)]
    new = list(old)
    changes = max(1, size // 100)
    for _ in range(changes):
        index = rng.randrange(len(new))
        new[index] = new[index].replace("compute", "recompute")
    for _ in range(max(1, changes // 2)):
        new.insert(rng.randrange(len(new)), f"    # inserted note {rng.random():.6f}")
    for _ in range(max(1, changes // 2)):
        del new[rng.randrange(len(new))]
    return old, new


def benchmark(size: int) -> Tuple[float, int]:
    old, new = make_pair(size)
    start = time.perf_counter()
    result = compare_documents(LoadedDocument("a", old), LoadedDocument("b", new))
    return time.perf_counter() - start, result.summary.total_changes


def main(argv: List[str]) -> None:
    sizes = [int(arg) for arg in argv] or DEFAULT_SIZES
    print(f"{'lines':>9} | {'changes':>8} | {'time':>9}")
    print("-" * 33)
    for size in sizes:
        elapsed, changes = benchmark(size)
        print(f"{size:>9,} | {changes:>8,} | {elapsed * 1000:>7.1f}ms")


if __name__ == "__main__":
    main(sys.argv[1:])
