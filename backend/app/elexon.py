"""Elexon BMRS client (FUELHH actuals + WINDFOR forecasts) with disk cache and a synthetic DEMO mode."""
import os, json, hashlib
from datetime import datetime, timedelta
from pathlib import Path
import httpx
import numpy as np
import pandas as pd

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
CACHE = Path(os.getenv("CACHE_DIR", "/tmp/elexon_cache"))
CACHE.mkdir(parents=True, exist_ok=True)
DEMO = os.getenv("DEMO_DATA") == "1"
FMT = "%Y-%m-%dT%H:%M:%SZ"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"  # bundled snapshot (built by scripts/build_snapshot.py)


def _snapshot(name: str):
    f = DATA_DIR / f"{name}.csv.gz"
    if not f.exists():
        return None
    df = pd.read_csv(f)
    for c in ("startTime", "publishTime"):
        if c in df:
            df[c] = pd.to_datetime(df[c], utc=True)
    return df


def _stream(dataset: str, params: dict) -> list[dict]:
    key = CACHE / (hashlib.md5(f"{dataset}{sorted(params.items())}".encode()).hexdigest() + ".json")
    if key.exists():
        return json.loads(key.read_text())
    r = httpx.get(f"{BASE}/{dataset}/stream", params=params, timeout=90)
    r.raise_for_status()
    data = r.json()
    key.write_text(json.dumps(data))
    return data


def _chunks(start: datetime, end: datetime, days: int):
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=days), end)
        yield cur, nxt
        cur = nxt


def fetch_actuals(start: datetime, end: datetime) -> pd.DataFrame:
    """Wind actuals (MW) per 30-min startTime (UTC)."""
    if DEMO:
        return _demo(start, end)[0]
    snap = _snapshot("actuals")
    if snap is not None:
        return snap
    rows = []
    for a, b in _chunks(start, end, 7):
        rows += _stream("FUELHH", {"settlementDateFrom": a.strftime("%Y-%m-%d"),
                                   "settlementDateTo": b.strftime("%Y-%m-%d"), "fuelType": "WIND"})
    df = pd.DataFrame(rows)
    df = df[df["fuelType"] == "WIND"].copy()
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df = df.rename(columns={"generation": "actual"})[["startTime", "actual"]]
    return df.drop_duplicates("startTime").sort_values("startTime").reset_index(drop=True)


def fetch_forecasts(pub_start: datetime, pub_end: datetime) -> pd.DataFrame:
    """All WINDFOR forecast vintages published in [pub_start, pub_end)."""
    if DEMO:
        return _demo(pub_start + timedelta(days=1), pub_end + timedelta(days=1))[1]
    snap = _snapshot("forecasts")
    if snap is not None:
        return snap
    rows = []
    for a, b in _chunks(pub_start, pub_end, 2):
        rows += _stream("WINDFOR", {"publishDateTimeFrom": a.strftime(FMT), "publishDateTimeTo": b.strftime(FMT)})
    df = pd.DataFrame(rows)
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df = df.rename(columns={"generation": "forecast"})[["startTime", "publishTime", "forecast"]]
    return df.drop_duplicates(["startTime", "publishTime"]).sort_values(["startTime", "publishTime"]).reset_index(drop=True)


def _demo(start, end):
    """Synthetic data for offline development/tests ONLY (never used unless DEMO_DATA=1)."""
    rng = np.random.default_rng(7)
    idx = pd.date_range(start, end, freq="30min", inclusive="left", tz="UTC")
    base = 8000 + 3500 * np.sin(np.arange(len(idx)) / 90) + rng.normal(0, 400, len(idx)).cumsum() / 20
    act = pd.DataFrame({"startTime": idx, "actual": np.clip(base, 200, 14000)})
    rows = []
    for pub in pd.date_range(start - timedelta(days=2), end, freq="3h", tz="UTC"):
        tg = act[(act.startTime > pub) & (act.startTime <= pub + timedelta(hours=48))]
        h = (tg.startTime - pub).dt.total_seconds() / 3600
        err = rng.normal(0, 150 + 60 * h)
        rows.append(pd.DataFrame({"startTime": tg.startTime, "publishTime": pub,
                                  "forecast": np.clip(tg.actual.values + err, 0, None)}))
    return act, pd.concat(rows, ignore_index=True)
