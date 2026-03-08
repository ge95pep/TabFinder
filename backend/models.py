"""
TabFinder — Data Models

All the Pydantic models that define how data flows through the app.
Scraper produces TabResult → Scorer adds scores → API returns SearchResponse.
"""

from pydantic import BaseModel, Field
from enum import Enum


# --- Enums ---

class TabType(str, Enum):
    """Tab format types available on jitashe.org"""
    IMAGE = "图片谱"      # Image-based tab (most common)
    GTP = "GTP谱"         # Guitar Pro format
    PDF = "PDF谱"         # PDF format
    CHORD = "和弦谱"      # Chord chart only
    ANY = "any"           # No preference


class PlayStyle(str, Enum):
    """Playing style categories"""
    STRUM = "弹唱"        # Sing-along strumming
    FINGERSTYLE = "指弹"  # Fingerpicking
    SOLO = "独奏"         # Solo arrangement
    ANY = "any"           # No preference


class Difficulty(str, Enum):
    """Difficulty preference"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    ANY = "any"


# --- Scraper Output ---

class TabResult(BaseModel):
    """
    Raw tab data as scraped from a source site.
    No scoring yet — just the facts.
    """
    title: str
    artist: str = ""
    url: str
    source: str = "jitashe.org"           # Which site it came from

    tab_type: str = ""                     # 图片谱, GTP谱, etc.
    tags: list[str] = Field(default_factory=list)  # 弹唱, 指弹, 前奏, solo, etc.

    views: int = 0
    num_ratings: int = 0
    accuracy_rating: float | None = None   # 准确度 (0-5 scale)
    difficulty_rating: float | None = None  # 难易度 (0-5 scale)

    uploader: str = ""
    uploader_url: str = ""


# --- Scorer Output ---

class ScoreBreakdown(BaseModel):
    """How the final score was calculated — transparency for the user."""
    accuracy: float = 0.0
    views: float = 0.0
    completeness: float = 0.0
    type_match: float = 0.0
    recency: float = 0.0


class ScoredTab(BaseModel):
    """A tab with its quality score attached. Ready for ranking."""
    rank: int = 0
    score: float = 0.0
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)

    # All original fields from TabResult
    title: str
    artist: str = ""
    url: str
    source: str = "jitashe.org"
    tab_type: str = ""
    tags: list[str] = Field(default_factory=list)
    views: int = 0
    num_ratings: int = 0
    accuracy_rating: float | None = None
    difficulty_rating: float | None = None
    uploader: str = ""
    uploader_url: str = ""


# --- API Models ---

class SearchRequest(BaseModel):
    """What the user sends to search for tabs."""
    song: str
    top_n: int = Field(default=3, ge=1, le=10)
    tab_type: TabType = TabType.ANY
    style: PlayStyle = PlayStyle.ANY
    difficulty: Difficulty = Difficulty.ANY


class SearchResponse(BaseModel):
    """What the API returns."""
    song: str
    source: str = "jitashe.org"
    results_found: int = 0                # Total tabs found before filtering
    top_tabs: list[ScoredTab] = Field(default_factory=list)
