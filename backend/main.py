"""
TabFinder — FastAPI Application

Single search endpoint that scrapes, scores, and returns the best guitar tabs.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.models import SearchResponse, ScoredTab, TabType, PlayStyle
from backend.scraper import jitashe
from backend.scorer import score_tabs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🎸 TabFinder starting up")
    yield
    logger.info("🎸 TabFinder shutting down")


app = FastAPI(
    title="TabFinder",
    description="Find the best guitar tabs, fast.",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow frontend dev server (Vite defaults to :5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/search", response_model=SearchResponse)
async def search_tabs(
    song: str = Query(..., min_length=1, description="Song name to search for"),
    top_n: int = Query(3, ge=1, le=10, description="Number of top results to return"),
    tab_type: TabType = Query(TabType.ANY, description="Preferred tab format"),
    style: PlayStyle = Query(PlayStyle.ANY, description="Preferred playing style"),
):
    """
    Search for guitar tabs and return the top N ranked by quality.

    Quality scoring considers: accuracy ratings, view count,
    completeness (section tags), tab type match, and rating count.
    """
    # Scrape
    raw_results = await jitashe.search(song)
    logger.info(f"Search '{song}': {len(raw_results)} raw results")

    # Score & rank
    top_tabs = score_tabs(
        raw_results,
        tab_type_pref=tab_type,
        style_pref=style,
        top_n=top_n,
    )

    return SearchResponse(
        song=song,
        source="jitashe.org",
        results_found=len(raw_results),
        top_tabs=top_tabs,
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "tabfinder"}
