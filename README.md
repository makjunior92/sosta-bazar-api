# Sosta Bazar API

FastAPI backend for comparing grocery prices across Bangladesh online stores.

## Stack

- FastAPI + PostgreSQL + Redis + Celery
- Playwright scrapers for Chaldal, Shwapno, MeenaClick, Daraz dMart

## Quick start

```bash
docker compose up --build
```

API docs: http://localhost:8000/docs

## Endpoints

- `GET /api/v1/search?q=butter` — Search and compare prices
- `GET /api/v1/search/stream?q=butter` — SSE live search progress
- `GET /api/v1/deals` — Best deals
- `GET /api/v1/stores` — Store health status

## Development

```bash
cp .env.example .env
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload
```
