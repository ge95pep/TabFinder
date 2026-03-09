"""
Scraper for guistudy.com (谱全了)

A Chinese guitar/ukulele tab site with structured data embedded in the page.
Search URL: /tabs?q={song_name}

Each result in the HTML contains:
  - Link: /tabs/{sheetCode}
  - Title text: "{song}吉他_{artist}_{key}调_原版{style}谱_高清{style}谱"
  - Difficulty: 零基础(1) / 初级(2) / 中级(3) / 高级(4) / 专业(5)
  - Views: e.g., "10.4万" or "3.6万"

HTML structure of search result list items:
  ul > li > a[href="/tabs/{id}"]
    ├── p.truncate (70% width) — full title string
    └── div (30% width)
          ├── p — difficulty level
          └── p — view count
"""

import os
import re
import logging
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup, Tag

from backend.models import TabResult

logger = logging.getLogger(__name__)

BASE_URL = "https://guistudy.com"
SEARCH_URL = f"{BASE_URL}/tabs"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# Proxy config — set HTTP_PROXY env var if needed
PROXY = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")

# Difficulty level mapping (numeric to descriptive)
DIFFICULTY_MAP = {
    "零基础": 1.0,
    "初级": 2.0,
    "中级": 3.0,
    "高级": 4.0,
    "专业": 5.0,
}

# Known tab styles that appear in the title string
STYLE_KEYWORDS = {"弹唱谱", "指弹谱", "和弦谱", "六线谱"}


async def search(song: str) -> list[TabResult]:
    """
    Search guistudy.com for tabs matching the song name.
    Returns all parsed results (unscored).
    """
    url = SEARCH_URL
    params = {"q": song}
    logger.info(f"Searching guistudy: {url}?q={song}")

    async with httpx.AsyncClient(
        headers=HEADERS,
        proxy=PROXY,
        timeout=15,
        follow_redirects=True,
    ) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    return _parse_search_results(soup)


def _parse_search_results(soup: BeautifulSoup) -> list[TabResult]:
    """Parse all tab results from the search page."""
    results: list[TabResult] = []

    # Results are <a> tags linking to /tabs/{id}
    for link in soup.select('a[href^="/tabs/"]'):
        href = link.get("href", "")
        # Skip non-tab links (like pagination, category links)
        if not re.match(r"^/tabs/[A-Za-z0-9]+$", href):
            continue

        result = _parse_result_link(link, href)
        if result:
            results.append(result)

    logger.info(f"Parsed {len(results)} tabs from guistudy")
    return results


def _parse_result_link(link: Tag, href: str) -> TabResult | None:
    """Parse a single <a> element into a TabResult."""

    url = f"{BASE_URL}{href}"

    # Get all <p> tags inside the link
    paragraphs = link.find_all("p")
    if not paragraphs:
        return None

    # First <p> with the long title string
    title_text = paragraphs[0].get_text(strip=True)
    if not title_text:
        return None

    # Parse the structured title: "{song}吉他_{artist}_{key}调_原版{style}谱_高清{style}谱"
    title, artist, tab_type, tags, key = _parse_title_string(title_text)

    # Extract difficulty and views from remaining <p> tags
    difficulty = None
    views = 0

    for p in paragraphs[1:]:
        text = p.get_text(strip=True)
        if text in DIFFICULTY_MAP:
            difficulty = DIFFICULTY_MAP[text]
        elif "万" in text:
            views = _parse_views(text)

    return TabResult(
        title=title,
        artist=artist,
        url=url,
        source="guistudy.com",
        tab_type=tab_type,
        tags=tags,
        views=views,
        num_ratings=0,  # guistudy doesn't show rating counts
        accuracy_rating=None,
        difficulty_rating=difficulty,
        uploader="",
        uploader_url="",
    )


def _parse_title_string(title_text: str) -> tuple[str, str, str, list[str], str]:
    """
    Parse guistudy's structured title format:
      "晴天吉他_周杰伦_G调_原版弹唱谱_高清弹唱谱"

    Returns: (title, artist, tab_type, tags, key)
    """
    title = ""
    artist = ""
    tab_type = ""
    tags: list[str] = []
    key = ""

    # Split by underscore
    parts = title_text.split("_")

    if len(parts) >= 1:
        # First part: "{song}吉他" — remove "吉他" suffix
        title = parts[0]
        for suffix in ["吉他", "尤克里里"]:
            if title.endswith(suffix):
                title = title[:-len(suffix)]
                break

    if len(parts) >= 2:
        artist = parts[1]

    if len(parts) >= 3:
        # Key info like "G调"
        key_part = parts[2]
        if key_part.endswith("调"):
            key = key_part[:-1]

    # Extract style/type from remaining parts
    remaining = "_".join(parts[3:]) if len(parts) > 3 else ""
    for style in STYLE_KEYWORDS:
        if style in remaining or style in title_text:
            tab_type = style
            # Also add as a tag (弹唱, 指弹, etc.)
            style_short = style.replace("谱", "")
            if style_short:
                tags.append(style_short)
            break

    if "原版" in remaining:
        tags.append("原版")

    return title, artist, tab_type, tags, key


def _parse_views(text: str) -> int:
    """
    Parse view count strings like "10.4万" or "3.6万" into integers.
    """
    text = text.strip()
    try:
        if "万" in text:
            num = float(text.replace("万", ""))
            return int(num * 10000)
        else:
            return int(text.replace(",", ""))
    except (ValueError, TypeError):
        return 0
