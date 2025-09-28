from __future__ import annotations

import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Deque, Dict


@dataclass
class Counter:
    name: str
    value: int = 0

    def inc(self, amount: int = 1) -> None:
        self.value += amount


@dataclass
class Histogram:
    name: str
    values: Deque[float] = field(default_factory=lambda: deque(maxlen=500))

    def observe(self, value: float) -> None:
        self.values.append(value)

    def percentile(self, pct: float) -> float:
        if not self.values:
            return 0.0
        data = sorted(self.values)
        index = int(len(data) * pct)
        index = min(index, len(data) - 1)
        return data[index]


class MetricsRegistry:
    def __init__(self) -> None:
        self.counters: Dict[str, Counter] = defaultdict(lambda: Counter(name="unknown"))
        self.histograms: Dict[str, Histogram] = {}

    def counter(self, name: str) -> Counter:
        counter = self.counters.get(name)
        if counter is None:
            counter = Counter(name=name)
            self.counters[name] = counter
        return counter

    def histogram(self, name: str) -> Histogram:
        histogram = self.histograms.get(name)
        if histogram is None:
            histogram = Histogram(name=name)
            self.histograms[name] = histogram
        return histogram
