"""
Abstract base for tab scrapers.
Each source site gets its own scraper class implementing this interface.
"""

from abc import ABC, abstractmethod
from backend.models import TabResult


class BaseScraper(ABC):
    """Interface that all tab source scrapers must implement."""

    @abstractmethod
    async def search(self, song: str) -> list[TabResult]:
        """
        Search for tabs matching the given song name.
        Returns ALL results found (scoring/filtering happens later).
        """
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name of this source (e.g., 'jitashe.org')"""
        ...
