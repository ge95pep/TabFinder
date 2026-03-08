"""
TabFinder — FastAPI Application

Multi-source search: queries jitashe (Chinese) and 911tabs (English) in parallel,
merges and ranks results, returns the best tabs.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.models import SearchResponse, TabResult, TabType, PlayStyle
from backend.scraper import jitashe, tabs911
from backend.scorer import score_tabs
from backend.cache import search_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Source(str, Enum):
    ALL = "all"
    JITASHE = "jitashe"
    TABS911 = "911tabs"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🎸 TabFinder starting up")
    yield
    logger.info("🎸 TabFinder shutting down")


app = FastAPI(
    title="TabFinder",
    description="Find the best guitar tabs, fast.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _fetch_source(name: str, coro) -> list[TabResult]:
    """Fetch from a source with error handling — one source failing shouldn't kill the search."""
    try:
        return await coro
    except Exception as e:
        logger.warning(f"Source {name} failed: {e}")
        return []


@app.get("/api/search", response_model=SearchResponse)
async def search_tabs(
    song: str = Query(..., min_length=1, description="Song name to search for"),
    top_n: int = Query(3, ge=1, le=10, description="Number of top results to return"),
    tab_type: TabType = Query(TabType.ANY, description="Preferred tab format"),
    style: PlayStyle = Query(PlayStyle.ANY, description="Preferred playing style"),
    source: Source = Query(Source.ALL, description="Which sources to search"),
):
    """
    Search for guitar tabs across multiple sources and return the top N ranked by quality.

    Sources:
    - jitashe: Chinese guitar tab community (best for Chinese songs)
    - 911tabs: English tab aggregator (Ultimate Guitar, guitartabs.cc, etc.)
    - all: Search both in parallel
    """
    cache_key = f"{source.value}:{song}:{tab_type.value}:{style.value}"
    cached = search_cache.get(cache_key)

    if cached is not None:
        raw_results = cached
        logger.info(f"Cache hit for '{song}': {len(raw_results)} results")
    else:
        # Build list of sources to query
        tasks: list[tuple[str, any]] = []
        if source in (Source.ALL, Source.JITASHE):
            tasks.append(("jitashe", jitashe.search(song)))
        if source in (Source.ALL, Source.TABS911):
            tasks.append(("911tabs", tabs911.search(song)))

        # Fetch all sources in parallel
        fetched = await asyncio.gather(
            *[_fetch_source(name, coro) for name, coro in tasks]
        )

        # Merge results
        raw_results: list[TabResult] = []
        for result_list in fetched:
            raw_results.extend(result_list)

        search_cache.set(cache_key, raw_results)
        logger.info(f"Search '{song}': {len(raw_results)} results from {len(tasks)} source(s)")

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique_results: list[TabResult] = []
    for r in raw_results:
        if r.url not in seen_urls:
            seen_urls.add(r.url)
            unique_results.append(r)

    # Score & rank
    top_tabs = score_tabs(
        unique_results,
        tab_type_pref=tab_type,
        style_pref=style,
        top_n=top_n,
    )

    source_label = "jitashe.org + 911tabs.com" if source == Source.ALL else source.value
    return SearchResponse(
        song=song,
        source=source_label,
        results_found=len(unique_results),
        top_tabs=top_tabs,
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "tabfinder", "version": "0.2.0"}


# --- Serve frontend static files ---
# Looks for built frontend in ../frontend/dist (dev) or ./static (Docker)
_frontend_dirs = [
    Path(__file__).parent.parent / "frontend" / "dist",  # dev
    Path(__file__).parent.parent / "static",              # docker
]

for _static_dir in _frontend_dirs:
    if _static_dir.is_dir():
        @app.get("/")
        async def index():
            return FileResponse(_static_dir / "index.html")

        # Mount static assets (JS, CSS) — must be after /api routes
        app.mount("/assets", StaticFiles(directory=_static_dir / "assets"), name="assets")

        # Catch-all for SPA routing (anything not /api/* falls back to index.html)
        @app.get("/{path:path}")
        async def spa_fallback(path: str):
            file_path = _static_dir / path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(_static_dir / "index.html")

        logger.info(f"Serving frontend from {_static_dir}")
        break
