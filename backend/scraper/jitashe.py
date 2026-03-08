"""
Scraper for jitashe.org (吉他社)

Search results page structure (from /search/tab/{song}/):
Each tab listing contains:
  - Title (with link to /tab/{id}/)
  - Artist (with link to /artist/{id}/)
  - Uploader (with link to /space/{id}/)
  - Ratings: 难易度 (difficulty) and 准确度 (accuracy)
  - Number of raters
  - View count
  - Tab type: 图片谱 / GTP谱 / PDF谱 / 和弦谱
  - Tags: 弹唱, 指弹, 前奏, 间奏, solo, 原版, etc.
"""

import asyncio
import re
import logging
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup, Tag

from backend.models import TabResult

logger = logging.getLogger(__name__)

BASE_URL = "https://www.jitashe.org"
SEARCH_URL = f"{BASE_URL}/search/tab/"
REQUEST_DELAY = 1.0  # seconds between requests — be polite

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


async def search(song: str) -> list[TabResult]:
    """
    Search jitashe.org for tabs matching the song name.
    Returns all parsed results (unscored).
    """
    url = f"{SEARCH_URL}{quote(song)}/"
    logger.info(f"Searching jitashe: {url}")

    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    return _parse_search_results(soup)


def _parse_search_results(soup: BeautifulSoup) -> list[TabResult]:
    """
    Parse the search results page into TabResult objects.

    The page structure uses a thread list where each item contains
    tab metadata. We need to handle multiple possible HTML structures
    since the site may vary layouts.
    """
    results: list[TabResult] = []

    # Strategy 1: Look for structured list items with tab links
    # Each result has a link to /tab/{id}/ — find all of them
    tab_links = soup.find_all("a", href=re.compile(r"/tab/\d+/"))

    # Deduplicate — same tab may appear multiple times in the page
    seen_urls: set[str] = set()

    for link in tab_links:
        href = link.get("href", "")
        full_url = href if href.startswith("http") else f"{BASE_URL}{href}"

        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        title = link.get_text(strip=True)
        if not title:
            continue

        # Walk up to find the parent container for this tab listing
        container = _find_tab_container(link)
        if container is None:
            continue

        result = _parse_single_tab(container, title, full_url)
        if result:
            results.append(result)

    logger.info(f"Parsed {len(results)} tabs from jitashe")
    return results


def _find_tab_container(element: Tag) -> Tag | None:
    """
    Walk up the DOM from a tab link to find the enclosing container
    that holds all the metadata for that tab listing.
    """
    # Typically the container is a <li>, <div>, or <tr> a few levels up
    current = element.parent
    for _ in range(8):  # don't walk too far
        if current is None:
            return None
        tag = current.name
        if tag in ("li", "tr", "article"):
            return current
        # Also check for divs with list-like classes
        if tag == "div":
            classes = " ".join(current.get("class", []))
            if any(kw in classes for kw in ["item", "list", "thread", "row", "entry"]):
                return current
        current = current.parent
    return element.parent  # fallback: use immediate parent


def _parse_single_tab(container: Tag, title: str, url: str) -> TabResult | None:
    """Extract all metadata from a single tab listing container."""
    text = container.get_text(" ", strip=True)

    # --- Artist ---
    artist = ""
    artist_link = container.find("a", href=re.compile(r"/artist/\d+/"))
    if artist_link:
        artist = artist_link.get_text(strip=True)

    # --- Uploader ---
    uploader = ""
    uploader_url = ""
    uploader_link = container.find("a", href=re.compile(r"/space/\d+/"))
    if uploader_link:
        uploader = uploader_link.get_text(strip=True)
        href = uploader_link.get("href", "")
        uploader_url = href if href.startswith("http") else f"{BASE_URL}{href}"

    # --- Tab type ---
    tab_type = ""
    for t in ["图片谱", "GTP谱", "PDF谱", "和弦谱"]:
        if t in text:
            tab_type = t
            break

    # --- Tags ---
    tags: list[str] = []
    tag_links = container.find_all("a", href=re.compile(r"/tag/\d+/"))
    for tl in tag_links:
        tag_text = tl.get_text(strip=True)
        if tag_text:
            tags.append(tag_text)

    # --- Views ---
    views = _extract_views(container)

    # --- Ratings ---
    accuracy, difficulty, num_ratings = _extract_ratings(container)

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


def _extract_views(container: Tag) -> int:
    """
    Extract view count from the container.
    Views appear as a large number in the listing (e.g., 1192947).
    """
    # Look for patterns like "1192947" that aren't part of URLs
    text = container.get_text(" ", strip=True)

    # Find standalone large numbers (likely view counts)
    # The view count is typically the largest number in the listing
    numbers = re.findall(r"(?<!\d)(\d{2,})(?!\d)", text)

    # Filter out numbers that look like IDs (from URLs) or dates
    candidates: list[int] = []
    for n in numbers:
        val = int(n)
        # View counts are typically > 10 and don't look like years
        if val > 10 and not (1990 <= val <= 2030):
            candidates.append(val)

    # The largest number is most likely the view count
    return max(candidates) if candidates else 0


def _extract_ratings(container: Tag) -> tuple[float | None, float | None, int]:
    """
    Extract accuracy rating, difficulty rating, and number of raters.
    Returns (accuracy, difficulty, num_ratings).

    Ratings show as: 难易度: [stars] 准确度: [stars] (N人评分)
    """
    text = container.get_text(" ", strip=True)

    num_ratings = 0
    rating_match = re.search(r"(\d+)\s*人评[分价]", text)
    if rating_match:
        num_ratings = int(rating_match.group(1))

    # Star ratings are tricky — they might be rendered as images or CSS classes
    # For now, we can check for star-related elements
    accuracy = _count_stars(container, "准确度")
    difficulty = _count_stars(container, "难易度")

    return accuracy, difficulty, num_ratings


def _count_stars(container: Tag, label: str) -> float | None:
    """
    Try to extract a star rating associated with a label.
    jitashe uses various methods to display stars — we try multiple strategies.
    """
    # Strategy 1: Look for elements with star-related classes after the label
    # Stars are often rendered as <i>, <span>, or <img> elements with class names
    # like "star", "icon-star", etc.

    # Strategy 2: Look for numeric rating in title/alt attributes
    # Some sites put "4.5" in a title attribute

    # For now, return None — we'll refine after testing with real HTML
    # The num_ratings alone is still a useful quality signal
    return None
