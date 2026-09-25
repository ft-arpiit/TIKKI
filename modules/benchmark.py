from __future__ import annotations

import time
from statistics import mean

from modules.router import LocalRouter


def main() -> None:
    router = LocalRouter()
    samples = []

    for _ in range(1000):
        start = time.perf_counter_ns()
        router.route("volume up")
        samples.append((time.perf_counter_ns() - start) / 1_000_000)

    print(f"mean_ms={mean(samples):.4f}")
    print(f"min_ms={min(samples):.4f}")
    print(f"max_ms={max(samples):.4f}")


if __name__ == "__main__":
    main()
