# TabFinder — Project Plan

> Find the best guitar tabs, fast. No more scrolling through garbage.

## Problem

Guitar tab sites (especially Chinese ones like jitashe.org) have tons of tabs per song, but quality varies wildly. You search "晴天" and get 50+ results — which ones are actually good? TabFinder answers that.

## How It Works

```
User enters song name
        ↓
Backend scrapes tab sources (jitashe.org, etc.)
        ↓
Parses results → extracts quality signals
        ↓
Scores & ranks by weighted formula
        ↓
Returns top N tabs with links + quality breakdown
```

## Tech Stack

| Layer    | Choice               | Why                                      |
| -------- | -------------------- | ---------------------------------------- |
| Backend  | Python + FastAPI     | Async, fast, clean API design            |
| Scraping | httpx + BeautifulSoup | jitashe is server-rendered, no JS needed |
| Frontend | React (Vite)         | Lightweight, good DX, easy to deploy     |
| Database | SQLite (optional)    | Cache results, store user preferences    |

## Data Sources

### Primary: jitashe.org (吉他社)
- **Search URL:** `https://www.jitashe.org/search/tab/{song_name}/`
- **Available signals per result:**
  - View count (e.g., 1,192,947 for top "晴天" tab)
  - Difficulty rating (难易度)
  - Accuracy rating (准确度)
  - Number of raters
  - Tab type: 图片谱 / GTP谱 / PDF谱 / 和弦谱
  - Tags: 弹唱, 指弹, 独奏, 前奏, 间奏, solo, 原版, 简单版, etc.
  - Uploader name + profile link
  - Tab detail URL: `/tab/{id}/`

### Future: Ultimate Guitar (for English songs)
- Well-known API/scraping patterns exist
- Would extend coverage beyond Chinese music

## Scoring Algorithm

Each tab gets a **quality score** (0–100) based on weighted signals:

| Signal                  | Weight | Logic                                                        |
| ----------------------- | ------ | ------------------------------------------------------------ |
| Accuracy rating (准确度) | 30%    | Direct quality indicator from community ratings               |
| Views                   | 25%    | Popularity = battle-tested. Log-scale to avoid mega-hits dominating |
| Completeness tags       | 20%    | More sections (前奏 + 间奏 + solo + 尾奏) = more complete tab |
| Tab type match          | 15%    | Bonus if matches user's preferred type                       |
| Recency                 | 10%    | Newer tabs may reflect updated arrangements                  |

**Adjustments:**
- "原版" (original version) tag → bonus points
- "简单版" (simplified) → neutral or slight penalty unless user wants easy tabs
- No ratings at all → penalty (unvalidated quality)

## User Settings

| Setting          | Options                              | Default    |
| ---------------- | ------------------------------------ | ---------- |
| Results count    | 1–10                                 | 3          |
| Tab type pref    | 图片谱 / GTP谱 / PDF谱 / 和弦谱 / Any | Any        |
| Style pref       | 弹唱 / 指弹 / 独奏 / Any             | Any        |
| Difficulty pref  | Easy / Medium / Hard / Any           | Any        |

## API Design

### `GET /api/search?song={name}&top_n=3&tab_type=any&style=any`

**Response:**
```json
{
  "song": "晴天",
  "source": "jitashe.org",
  "results_found": 47,
  "top_tabs": [
    {
      "rank": 1,
      "title": "晴天",
      "artist": "周杰伦",
      "score": 92.5,
      "url": "https://www.jitashe.org/tab/9895/",
      "tab_type": "图片谱",
      "tags": ["弹唱"],
      "views": 1192947,
      "accuracy_rating": 4.5,
      "difficulty_rating": 3.0,
      "num_ratings": 2,
      "uploader": "泉州天虹乐器",
      "score_breakdown": {
        "accuracy": 27.0,
        "views": 25.0,
        "completeness": 14.0,
        "type_match": 15.0,
        "recency": 6.0
      }
    }
  ]
}
```

## Project Structure

```
TabFinder/
├── PLAN.md              ← you are here
├── README.md            ← user-facing docs
├── backend/
│   ├── main.py          ← FastAPI app entry
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── jitashe.py   ← jitashe.org scraper
│   │   └── base.py      ← abstract scraper interface
│   ├── scorer.py        ← quality scoring engine
│   ├── models.py        ← Pydantic models
│   └── requirements.txt
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   └── ...
│   └── ...
└── .gitignore
```

## Milestones

### Phase 1 — Core Backend (MVP)
- [x] Project scaffolding (FastAPI + deps)
- [x] jitashe.org scraper (search + parse results)
- [x] Scoring engine with weighted formula
- [x] `/api/search` endpoint returning ranked tabs
- [x] Basic error handling + rate limiting (be nice to jitashe)

### Phase 2 — Frontend
- [x] React app with search bar
- [x] Results display with score breakdown
- [x] User preference controls (tab type, style, top N)
- [x] Mobile-friendly responsive design

### Phase 3 — Polish & Extend
- [x] Result caching (avoid re-scraping same song within N minutes)
- [x] 911tabs.com as second source (English songs) — UG blocked by Cloudflare
- [x] Multi-source result merging & dedup
- [x] Deploy (Docker + docker-compose)

### Phase 4 — Nice to Have
- [ ] User accounts + saved searches
- [ ] "Tab of the day" / trending
- [ ] Browser extension for quick lookup
- [ ] Comparison view (side-by-side tabs)

## Notes

- **Be respectful to jitashe.org:** Add delays between requests, cache aggressively, include a reasonable User-Agent. We're not trying to DDoS them.
- **Tab content itself is NOT scraped** — we only scrape search result metadata (titles, ratings, views, links). Users click through to the source site to view the actual tab. This keeps us on the right side of copyright.
- **No login required** for search results page — all quality signals are visible without authentication.
