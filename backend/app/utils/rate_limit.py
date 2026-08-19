"""In-process sliding-window rate limiting.

Deliberately dependency-free: the demo runs a single uvicorn worker, so an
in-memory window is enough to blunt credential stuffing. A multi-worker or
multi-replica deployment should back ``RateLimiter`` with Redis instead, since
each process would otherwise keep its own counters.
"""

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    """Counts events per key inside a rolling time window."""

    def __init__(self, *, max_events: int, window_seconds: int) -> None:
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        events = self._events[key]
        cutoff = now - self.window_seconds
        while events and events[0] <= cutoff:
            events.popleft()
        return events

    def retry_after(self, key: str) -> int | None:
        """Return seconds to wait if ``key`` is over budget, else ``None``."""
        now = time.monotonic()
        with self._lock:
            events = self._prune(key, now)
            if len(events) < self.max_events:
                return None
            return max(1, int(self.window_seconds - (now - events[0])) + 1)

    def record(self, key: str) -> None:
        """Record one event against ``key``."""
        now = time.monotonic()
        with self._lock:
            self._prune(key, now).append(now)

    def reset(self, key: str) -> None:
        """Forget the history for ``key`` (called after a successful login)."""
        with self._lock:
            self._events.pop(key, None)

    def clear(self) -> None:
        """Drop every counter. Used by tests."""
        with self._lock:
            self._events.clear()
