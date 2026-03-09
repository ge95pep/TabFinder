# 🎸 TabFinder

Find the best guitar tabs, fast. Searches multiple sources, scores quality, returns the top picks.

## Features

- **Multi-source search** — [吉他社](https://www.jitashe.org) (Chinese) + [谱全了](https://guistudy.com) (Chinese) + [911Tabs](https://www.911tabs.com) (English)
- **Quality scoring** — Weighted algorithm considers accuracy ratings, popularity, completeness, and more
- **Transparent ranking** — See exactly why each tab scored the way it did
- **Filter by preference** — Tab type, playing style, number of results
- **Fast** — Parallel fetching + 10-minute result cache

## Quick Start

### Development

```bash
# Backend
conda create -n tabfinder python=3.12 -y
conda activate tabfinder
pip install -r backend/requirements.txt
uvicorn backend.main:app --port 8888

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and search!

### Docker

```bash
docker compose up --build
# → http://localhost:8888
```

## API

```
GET /api/search?song=晴天&top_n=3&source=all&tab_type=any&style=any

# Source options: all, jitashe, guistudy, 911tabs
GET /api/health
```

## Scoring

Each tab is scored 0–100 based on:

| Signal | Weight | Description |
|--------|--------|-------------|
| Accuracy | 30% | Community accuracy rating |
| Popularity | 25% | Views (log-scaled) or vote count |
| Completeness | 20% | Section tags (前奏, 间奏, solo, etc.) |
| Type match | 15% | Bonus if tab type matches preference |
| Validated | 10% | Bonus for having multiple ratings |

## Tech Stack

- **Backend:** Python, FastAPI, httpx, BeautifulSoup
- **Frontend:** React, Vite
- **Deployment:** Docker

## License

MIT
