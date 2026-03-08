"""
Scraper for 911tabs.com — a tab aggregator for English songs.

911tabs aggregates tabs from multiple sources (Ultimate Guitar, guitartabs.cc, etc.)
and provides its own rating system. Great complement to jitashe for English music.

HTML structure of song page (/tabs/{letter}/{artist}/{song}_tab.htm):

a.ov-h                          ← one per tab version
  ├── div.num                   ← rank number
  ├── div.description
  │     ├── div.name            ← song title + tab type
  │     └── div.site            ← source URL
  ├── div.type.{type-class}     ← tab type (guitar, guitar-pro, chords, etc.)
  └── div.rating
        └── div.small-rating
              └── i.on / i      ← filled/empty stars (count i.on for rating)

Search page (/search.php?search={query}&type=any):
Returns links to song pages at /tabs/{letter}/{artist}/{song}_tab.htm
"""

import re
import logging
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup, Tag

from backend.models import TabResult

logger = logging.getLogger(__name__)

BASE_URL = "https://www.911tabs.com"
SEARCH_URL = f"{BASE_URL}/search.php"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

PROXY = "http://127.0.0.1:7890/"

# Map 911tabs type classes to our tab types
TYPE_MAP = {
    "guitar-pro": "Guitar Pro",
    "guitar": "Guitar Tab",
    "chords": "Chords",
    "bass": "Bass Tab",
    "drum": "Drum Tab",
    "power": "Power Tab",
    "tab-pro": "Pro",
    "ukulele": "Ukulele",
    "video": "Video",
}


async def search(song: str) -> list[TabResult]:
    """
    Search 911tabs for a song. This is a two-step process:
    1. Search → get the song page URL
    2. Fetch song page → parse all tab versions

    Returns all tab versions found for the best matching song.
    """
    logger.info(f"Searching 911tabs for: {song}")

    async with httpx.AsyncClient(
        headers=HEADERS,
        proxy=PROXY,
        timeout=15,
        follow_redirects=True,
    ) as client:
        # Step 1: Search
        resp = await client.get(
            SEARCH_URL,
            params={"search": song, "type": "any"},
        )
        resp.raise_for_status()

        song_urls = _parse_search_results(resp.text)
        if not song_urls:
            logger.info("No results found on 911tabs")
            return []

        # Step 2: Fetch the top song page (most relevant match)
        # Could fetch multiple in the future for broader results
        song_url = song_urls[0]
        logger.info(f"Fetching song page: {song_url}")

        resp = await client.get(song_url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    return _parse_song_page(soup, song)


def _parse_search_results(html: str) -> list[str]:
    """Parse search results page to extract song page URLs."""
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []

    # Song links follow pattern: /tabs/{letter}/{artist}/{song}_tab.htm
    for link in soup.find_all("a", href=re.compile(r"/tabs/\w/[\w_]+/[\w_]+_tab\.htm")):
        href = link.get("href", "")
        full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
        if full_url not in urls:
            urls.append(full_url)

    return urls


def _parse_song_page(soup: BeautifulSoup, search_query: str) -> list[TabResult]:
    """Parse a 911tabs song page into TabResult objects."""
    results: list[TabResult] = []

    # Each tab version is an <a class="ov-h"> element
    for item in soup.select("a.ov-h"):
        result = _parse_tab_item(item, search_query)
        if result:
            results.append(result)

    logger.info(f"Parsed {len(results)} tabs from 911tabs")
    return results


def _parse_tab_item(item: Tag, search_query: str) -> TabResult | None:
    """Parse a single tab version from the song page."""

    # --- Title ---
    name_el = item.select_one("div.name span")
    title = name_el.get_text(strip=True) if name_el else search_query

    # --- URL (actual tab source) ---
    data_url = item.get("data-url", "")
    href = item.get("href", "")

    # Prefer data-url (actual source), fall back to 911tabs redirect link
    if data_url:
        url = data_url if data_url.startswith("http") else f"https://{data_url}"
    elif href:
        url = href if href.startswith("http") else f"{BASE_URL}{href}"
    else:
        return None

    # Skip "pro" tabs (paid UG feature)
    type_el = item.select_one("div.type")
    type_classes = type_el.get("class", []) if type_el else []

    if "tab-pro" in type_classes:
        return None  # paid content, not useful

    # --- Tab type ---
    tab_type = ""
    for cls in type_classes:
        if cls in TYPE_MAP:
            tab_type = TYPE_MAP[cls]
            break
    if not tab_type and type_el:
        tab_type = type_el.get_text(strip=True).title()

    # --- Rating (star count) ---
    stars = 0
    small_rating = item.select_one("div.small-rating")
    if small_rating:
        stars = len(small_rating.select("i.on"))

    # --- Votes (number in parentheses in div.rating) ---
    num_ratings = 0
    rating_div = item.select_one("div.rating")
    if rating_div:
        text = rating_div.get_text(strip=True)
        match = re.search(r"\((\d+)\)", text)
        if match:
            num_ratings = int(match.group(1))

    # --- Source site ---
    site_el = item.select_one("div.site")
    source_site = site_el.get_text(strip=True) if site_el else "911tabs.com"

    # Build tags from type info
    tags: list[str] = []
    type_text = type_el.get_text(strip=True) if type_el else ""
    if type_text:
        tags.append(type_text)

    return TabResult(
        title=title,
        artist="",  # Artist comes from the page context, not individual items
        url=url,
        source=f"911tabs ({source_site})",
        tab_type=tab_type,
        tags=tags,
        views=0,  # 911tabs doesn't show view counts
        num_ratings=num_ratings,
        accuracy_rating=float(stars) if stars > 0 else None,
        difficulty_rating=None,
        uploader="",
        uploader_url="",
    )
