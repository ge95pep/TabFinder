"""
TabFinder — Scoring Engine

Takes raw TabResult objects and produces ranked ScoredTab objects.
Each tab is scored 0–100 based on weighted quality signals.
"""

import math
import logging

from backend.models import (
    TabResult,
    ScoredTab,
    ScoreBreakdown,
    TabType,
    PlayStyle,
)

logger = logging.getLogger(__name__)

# --- Weight configuration ---
# These should add up to 1.0
WEIGHT_ACCURACY = 0.30
WEIGHT_VIEWS = 0.25
WEIGHT_COMPLETENESS = 0.20
WEIGHT_TYPE_MATCH = 0.15
WEIGHT_RATINGS_EXIST = 0.10  # bonus for having been rated at all

# Tags that indicate a more complete tab
COMPLETENESS_TAGS = {"前奏", "间奏", "尾奏", "solo", "原版"}
# Max completeness tags we'd expect
MAX_COMPLETENESS_TAGS = len(COMPLETENESS_TAGS)

# Bonus/penalty tags
BONUS_TAGS = {"原版": 5.0}  # "original version" is a quality signal
PENALTY_TAGS = {"简单版": -3.0}  # simplified = less complete (slight penalty)


def score_tabs(
    tabs: list[TabResult],
    tab_type_pref: TabType = TabType.ANY,
    style_pref: PlayStyle = PlayStyle.ANY,
    top_n: int = 3,
) -> list[ScoredTab]:
    """
    Score and rank a list of tabs. Returns the top N.

    Scoring formula (each component normalized to 0–100, then weighted):
      - Accuracy rating (30%): community accuracy rating
      - Views (25%): log-scaled popularity
      - Completeness (20%): how many section tags (前奏, 间奏, solo, etc.)
      - Type match (15%): bonus if tab type matches user preference
      - Ratings exist (10%): bonus for having ratings (validated quality)
    """
    if not tabs:
        return []

    # Pre-compute max views for normalization
    max_views = max((t.views for t in tabs), default=1)
    if max_views == 0:
        max_views = 1

    scored: list[ScoredTab] = []

    for tab in tabs:
        breakdown = _compute_scores(tab, max_views, tab_type_pref, style_pref)
        total = (
            breakdown.accuracy * WEIGHT_ACCURACY
            + breakdown.views * WEIGHT_VIEWS
            + breakdown.completeness * WEIGHT_COMPLETENESS
            + breakdown.type_match * WEIGHT_TYPE_MATCH
            + breakdown.recency * WEIGHT_RATINGS_EXIST
        )

        scored.append(ScoredTab(
            score=round(total, 1),
            score_breakdown=breakdown,
            title=tab.title,
            artist=tab.artist,
            url=tab.url,
            source=tab.source,
            tab_type=tab.tab_type,
            tags=tab.tags,
            views=tab.views,
            num_ratings=tab.num_ratings,
            accuracy_rating=tab.accuracy_rating,
            difficulty_rating=tab.difficulty_rating,
            uploader=tab.uploader,
            uploader_url=tab.uploader_url,
        ))

    # Sort by score descending, assign ranks
    scored.sort(key=lambda t: t.score, reverse=True)
    for i, tab in enumerate(scored[:top_n], start=1):
        tab.rank = i

    return scored[:top_n]


def _compute_scores(
    tab: TabResult,
    max_views: int,
    tab_type_pref: TabType,
    style_pref: PlayStyle,
) -> ScoreBreakdown:
    """Compute individual score components (each 0–100)."""

    # --- Accuracy (0–100) ---
    if tab.accuracy_rating is not None:
        # Star level is 1–5 from CSS class
        clamped = min(max(tab.accuracy_rating, 0.0), 5.0)
        accuracy_score = (clamped / 5.0) * 100
    elif tab.num_ratings > 0:
        # Has ratings but we couldn't parse the stars — give partial credit
        accuracy_score = 50.0
    else:
        # No ratings at all
        accuracy_score = 30.0  # neutral baseline, not zero

    # --- Views (0–100, log-scaled) ---
    if tab.views > 0 and max_views > 0:
        # Log scale so 1M views doesn't totally crush 100K views
        views_score = (math.log1p(tab.views) / math.log1p(max_views)) * 100
    else:
        views_score = 0.0

    # --- Completeness (0–100) ---
    tag_set = set(tab.tags)
    completeness_hits = len(tag_set & COMPLETENESS_TAGS)
    completeness_score = (completeness_hits / MAX_COMPLETENESS_TAGS) * 100

    # Apply bonus/penalty tags
    for tag, bonus in BONUS_TAGS.items():
        if tag in tag_set:
            completeness_score = min(100, completeness_score + bonus)
    for tag, penalty in PENALTY_TAGS.items():
        if tag in tag_set:
            completeness_score = max(0, completeness_score + penalty)

    # --- Type match (0 or 100) ---
    if tab_type_pref == TabType.ANY:
        type_score = 50.0  # neutral when no preference
    elif tab.tab_type == tab_type_pref.value:
        type_score = 100.0
    else:
        type_score = 10.0  # small score — still a valid tab, just not preferred type

    # Style preference (folded into type_match for simplicity)
    if style_pref != PlayStyle.ANY:
        if style_pref.value in tag_set:
            type_score = min(100, type_score + 20)

    # --- Ratings exist (0 or 100) ---
    # Tabs that have been rated are more trustworthy
    if tab.num_ratings >= 3:
        ratings_score = 100.0
    elif tab.num_ratings >= 1:
        ratings_score = 60.0
    else:
        ratings_score = 0.0

    return ScoreBreakdown(
        accuracy=round(accuracy_score, 1),
        views=round(views_score, 1),
        completeness=round(completeness_score, 1),
        type_match=round(type_score, 1),
        recency=round(ratings_score, 1),  # reusing "recency" field for ratings_exist
    )
