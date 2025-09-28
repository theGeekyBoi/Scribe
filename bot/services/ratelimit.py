from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass(slots=True)
class TokenBucket:
    rate: float
    capacity: int
    tokens: float
    updated_at: float

    def __init__(self, rate: float, capacity: int) -> None:
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.updated_at = time.perf_counter()

    def consume(self, amount: float) -> bool:
        now = time.perf_counter()
        elapsed = now - self.updated_at
        self.updated_at = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False


class RateLimiter:
    def __init__(self, rate: float, capacity: int) -> None:
        self.bucket = TokenBucket(rate, capacity)
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        while True:
            async with self._lock:
                if self.bucket.consume(tokens):
                    return
            await asyncio.sleep(max(1 / self.bucket.rate, 0.01))


class rate_limited:
    def __init__(self, limiter: RateLimiter, tokens: float = 1.0) -> None:
        self.limiter = limiter
        self.tokens = tokens

    async def __aenter__(self) -> None:
        await self.limiter.acquire(self.tokens)

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None
