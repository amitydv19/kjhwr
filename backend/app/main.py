import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from . import service

app = FastAPI(title="Wind forecast decision-support API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])
DEMO = os.getenv("DEMO_DATA") == "1"


@app.get("/api/health")
def health():
    return {"ok": True, "demo_data": DEMO}


@app.get("/api/config")
def config():
    return {"delivery_dates": [f"2026-01-{d:02d}" for d in range(2, 32)] + ["2026-02-01"],
            "default_cutoff_hour": service.DEFAULT_CUTOFF_HOUR, "demo_data": DEMO}


@app.get("/api/decision/{date}")
def decision(date: str, cutoff_hour: float = Query(service.DEFAULT_CUTOFF_HOUR, ge=0, le=23.5)):
    try:
        return service.day_view(date, cutoff_hour)
    except Exception as e:
        raise HTTPException(502, f"Failed to build view: {e}")


@app.get("/api/metrics")
def metrics(cutoff_hour: float = Query(service.DEFAULT_CUTOFF_HOUR, ge=0, le=23.5)):
    try:
        return service.metrics(cutoff_hour)
    except Exception as e:
        raise HTTPException(502, f"Failed to compute metrics: {e}")


static = Path(os.getenv("STATIC_DIR", "static"))
if static.exists():
    app.mount("/", StaticFiles(directory=static, html=True), name="static")
