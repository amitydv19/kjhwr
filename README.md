# Wind Forecast Desk (GB day-ahead decision support)

Web app for a UK utility's day-ahead power desk. It shows (1) the latest wind forecast **available at the time the
day-ahead purchase decision is made** and (2) how accurate those forecasts were, so the desk can size a buffer.
Scope: national wind only, Elexon BMRS `FUELHH` (actuals) and `WINDFOR` (forecasts), decisions made in **January 2026**.

**AI disclosure:** this project was built with AI assistance (Claude / Cursor). I reviewed and tested all logic.

## Live app
<PASTE HEROKU/VERCEL URL HERE>

## Key modelling decisions
- Decisions in Jan 2026 are for delivery on the next London day (delivery 2 Jan – 1 Feb 2026).
- For each half-hour target, we use the **latest WINDFOR forecast with `publishTime` ≤ cut-off** on D-1
  (default 09:00 London, ~EPEX day-ahead gate closure; adjustable in the UI). No look-ahead (unit-tested).
- Error = forecast − actual. Positive = over-forecast = wind shortfall = extra MW to buy.
- Metrics: MAE, RMSE, bias, WAPE, P90 abs error, P90 shortfall ("suggested buffer"), by day / hour / horizon.

## Structure
```
backend/app/elexon.py    Elexon client (chunked, disk-cached) + DEMO synthetic data (DEMO_DATA=1, tests only)
backend/app/service.py   decision-time forecast selection + metrics
backend/app/main.py      FastAPI: /api/config, /api/decision/{date}, /api/metrics, serves built React
backend/tests/           pytest (no look-ahead, uniqueness, metrics)
frontend/src/App.jsx     React dashboard (Recharts)
Dockerfile               multi-stage: build React -> serve with FastAPI
heroku.yml               Heroku container deploy
```

## Run
```bash
docker compose up --build          # http://localhost:8000  (first load fetches Elexon, ~30s, then cached)
# dev without docker
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev      # http://localhost:5173 (proxies /api)
# tests
cd backend && DEMO_DATA=1 pytest
```

## Deploy (Heroku, container stack)
```bash
heroku create && heroku stack:set container && git push heroku main
```

## Limitations / next steps
National level only; no price data; cache is ephemeral on Heroku (pre-warm or persist to storage); gate-closure
time is an assumption; could add probabilistic bands and alerting.

## Vercel deployment (what is actually deployed)
Vercel hosts the React build as static files and FastAPI as a serverless function (`api/index.py`, see `vercel.json`).
Because Jan 2026 is historical, data is bundled as a snapshot (`backend/data/*.csv.gz`) built once by
`scripts/build_snapshot.py`, so requests don't depend on Elexon uptime or function timeouts. Docker is used for local/Heroku runs.
