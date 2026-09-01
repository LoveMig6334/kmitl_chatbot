"""Tiny in-memory sliding-window rate limiter keyed by client IP.

The ThaiLLM quota is shared by the whole team, so every deployment gets a
default cap.  Single-process only; put a real limiter in front for multi-worker
deployments.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, per_minute: int, window_s: float = 60.0):
        self.per_minute = per_minute
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    @property
    def enabled(self) -> bool:
        return self.per_minute > 0

    def check(self, key: str, now: float | None = None) -> float | None:
        """Record a hit; return seconds to wait if the caller is over the limit, else None."""
        if not self.enabled:
            return None
        now = time.monotonic() if now is None else now
        q = self._hits[key]
        cutoff = now - self.window_s
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= self.per_minute:
            return max(0.0, q[0] + self.window_s - now)
        q.append(now)
        return None
