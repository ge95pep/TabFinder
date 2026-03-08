"""
TabFinder — Simple in-memory cache with TTL.

Avoids hammering jitashe.org when the same song is searched repeatedly.
Cache key = (song, source). TTL default = 10 minutes.
"""

import time
import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TTL = 600  # 10 minutes


class Cache:
    def __init__(self, ttl: int = DEFAULT_TTL):
        self._store: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Any | None:
        """Return cached value if exists and not expired, else None."""
        if key not in self._store:
            return None

        ts, value = self._store[key]
        if time.time() - ts > self._ttl:
            del self._store[key]
            logger.debug(f"Cache expired: {key}")
            return None

        logger.debug(f"Cache hit: {key}")
        return value

    def set(self, key: str, value: Any) -> None:
        """Store value with current timestamp."""
        self._store[key] = (time.time(), value)
        logger.debug(f"Cache set: {key}")
        self._cleanup()

    def _cleanup(self) -> None:
        """Remove expired entries (lazy, runs on set)."""
        now = time.time()
        expired = [k for k, (ts, _) in self._store.items() if now - ts > self._ttl]
        for k in expired:
            del self._store[k]


# Singleton
search_cache = Cache()
