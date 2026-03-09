"""
Scraper for jitashe.org (吉他社)

HTML structure of search results (from /search/tab/{song}/):

div.tab-list#threadlist
  └── div.tab-item              ← one per tab result
        ├── div.icon            ← thumbnail
        └── div.text
              ├── a.title       ← tab title + link to /tab/{id}/
              ├── div.rating-g  ← ratings block
              │     ├── fieldset.star-level title="{score}"  ← 难易度
              │     ├── fieldset.star-level title="{score}"  ← 准确度
              │     └── span.rating-k "(N人评分)"
              ├── div.info      ← artist, uploader, views, replies
              │     ├── a.title2 href="/artist/{id}/"
              │     ├── a href="/space/{id}/"   ← uploader
              │     ├── span after icon-chakan  ← view count
              │     └── span after icon-huifu   ← reply count
              └── div.tags      ← tag links + tab type
"""

import os
import re
import logging
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup, Tag

from backend.models import TabResult

logger = logging.getLogger(__name__)

BASE_URL = "https://www.jitashe.org"
SEARCH_URL = f"{BASE_URL}/search/tab/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# Proxy config — set HTTP_PROXY env var if needed (e.g., behind GFW)
PROXY = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")

TAB_TYPES = {"图片谱", "GTP谱", "PDF谱", "和弦谱"}


async def search(song: str) -> list[TabResult]:
    """
    Search jitashe.org for tabs matching the song name.
    Returns all parsed results (unscored).
    """
    url = f"{SEARCH_URL}{quote(song)}/"
    logger.info(f"Searching jitashe: {url}")

    async with httpx.AsyncClient(
        headers=HEADERS,
        proxy=PROXY,
        timeout=15,
        follow_redirects=True,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    return _parse_search_results(soup)


def _parse_search_results(soup: BeautifulSoup) -> list[TabResult]:
    """Parse all div.tab-item containers into TabResult objects."""
    items = soup.select("div.tab-item")
    logger.info(f"Found {len(items)} tab-item containers")

    results: list[TabResult] = []
    for item in items:
        result = _parse_tab_item(item)
        if result:
            results.append(result)

    return results


def _parse_tab_item(item: Tag) -> TabResult | None:
    """Parse a single div.tab-item into a TabResult."""

    # --- Title & URL ---
    title_el = item.select_one("a.title")
    if not title_el:
        return None

    title = title_el.get_text(strip=True)
    href = title_el.get("href", "")
    url = href if href.startswith("http") else f"{BASE_URL}{href}"

    # --- Artist ---
    artist = ""
    artist_el = item.select_one("a.title2")
    if artist_el:
        artist = artist_el.get_text(strip=True)

    # --- Uploader ---
    uploader = ""
    uploader_url = ""
    uploader_el = item.select_one('a[href*="/space/"]')
    if uploader_el:
        uploader = uploader_el.get_text(strip=True)
        up_href = uploader_el.get("href", "")
        uploader_url = up_href if up_href.startswith("http") else f"{BASE_URL}{up_href}"

    # --- Ratings ---
    difficulty, accuracy, num_ratings = _parse_ratings(item)

    # --- Views ---
    views = _parse_views(item)

    # --- Tab type & Tags ---
    tab_type, tags = _parse_tags(item)

    return TabResult(
        title=title,
        artist=artist,
        url=url,
        source="jitashe.org",
        tab_type=tab_type,
        tags=tags,
        views=views,
        num_ratings=num_ratings,
        accuracy_rating=accuracy,
        difficulty_rating=difficulty,
        uploader=uploader,
        uploader_url=uploader_url,
    )


def _parse_ratings(item: Tag) -> tuple[float | None, float | None, int]:
    """
    Extract difficulty, accuracy, and num_ratings from the rating block.

    Structure:
      fieldset.star-level.star-level-{N}  (CSS class = displayed star level 1–5)
      First fieldset = 难易度, second = 准确度
      span.rating-k containing "(N人评分)"

    The CSS class `star-level-N` is the reliable rating (1–5 scale).
    The `title` attribute is the raw sum across all raters (not useful directly).
    """
    difficulty = None
    accuracy = None
    num_ratings = 0

    # Number of raters
    rating_block = item.select_one("div.rating-g")
    if rating_block:
        match = re.search(r"\((\d+)人评[分价]\)", rating_block.get_text())
        if match:
            num_ratings = int(match.group(1))

    # Star ratings from CSS class
    fieldsets = item.select("fieldset.star-level")
    if len(fieldsets) >= 1:
        difficulty = _star_level_from_class(fieldsets[0])
    if len(fieldsets) >= 2:
        accuracy = _star_level_from_class(fieldsets[1])

    return difficulty, accuracy, num_ratings


def _star_level_from_class(fieldset: Tag) -> float | None:
    """Extract star level (1–5) from CSS class like 'star-level-3'."""
    classes = fieldset.get("class", [])
    for cls in classes:
        match = re.match(r"star-level-(\d+)", cls)
        if match:
            return float(match.group(1))
    return None


def _parse_views(item: Tag) -> int:
    """
    Extract view count. Structure:
      <span class="iconfont icon-chakan"></span>
      <span>1192947</span>
    """
    icon = item.select_one("span.icon-chakan")
    if icon:
        # The view count is in the next sibling span
        next_span = icon.find_next_sibling("span")
        if next_span:
            text = next_span.get_text(strip=True)
            try:
                return int(text)
            except ValueError:
                pass
    return 0


def _parse_tags(item: Tag) -> tuple[str, list[str]]:
    """
    Extract tab type and tags from the tags section.
    Tab type appears as plain text (图片谱, GTP谱, etc.)
    Tags appear as links to /tag/{id}/.

    Returns (tab_type, [tag1, tag2, ...])
    """
    tab_type = ""
    tags: list[str] = []

    # Check full text for tab type keywords
    text = item.get_text(" ", strip=True)
    for t in TAB_TYPES:
        if t in text:
            tab_type = t
            break

    # Tag links
    tag_links = item.select('a[href*="/tag/"]')
    for tl in tag_links:
        tag_text = tl.get_text(strip=True)
        if tag_text and tag_text not in TAB_TYPES:
            tags.append(tag_text)

    return tab_type, tags
