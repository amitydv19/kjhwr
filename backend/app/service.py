"""Core analytics: which forecast was available at decision time, and how accurate was it."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from . import elexon

LONDON = ZoneInfo("Europe/London")
# Decisions are made in Jan 2026 for the NEXT delivery day (day-ahead): delivery 2 Jan .. 1 Feb 2026.
DECISION_START = datetime(2026, 1, 1, tzinfo=timezone.utc)
DECISION_END = datetime(2026, 2, 1, tzinfo=timezone.utc)  # exclusive
DEFAULT_CUTOFF_HOUR = 9.0  # 09:00 London on D-1 (~EPEX day-ahead gate closure); user-configurable


@lru_cache(maxsize=1)
def load_raw():
    actuals = elexon.fetch_actuals(DECISION_START + timedelta(days=1), DECISION_END + timedelta(days=1))
    fc = elexon.fetch_forecasts(DECISION_START, DECISION_END)
    return actuals, fc


def decision_forecast(fc: pd.DataFrame, cutoff_hour: float) -> pd.DataFrame:
    """For each target half-hour, the LATEST forecast published at/before cutoff on the previous London day."""
    df = fc.copy()
    tgt_day = df["startTime"].dt.tz_convert(LONDON).dt.normalize().dt.tz_localize(None)
    cutoff_local = tgt_day - pd.Timedelta(days=1) + pd.Timedelta(hours=cutoff_hour)
    df["cutoff"] = cutoff_local.dt.tz_localize(LONDON, ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC")
    df = df[df["publishTime"] <= df["cutoff"]]
    df = df.sort_values("publishTime").drop_duplicates("startTime", keep="last")
    return df.sort_values("startTime").reset_index(drop=True)


def joined(cutoff_hour: float) -> pd.DataFrame:
    actuals, fc = load_raw()
    d = decision_forecast(fc, cutoff_hour).merge(actuals, on="startTime", how="inner")
    d["error"] = d["forecast"] - d["actual"]  # +ve = over-forecast => wind SHORTFALL => buy more
    local = d["startTime"].dt.tz_convert(LONDON)
    d["date"] = local.dt.strftime("%Y-%m-%d")
    d["hour"] = local.dt.hour
    d["horizon_h"] = (d["startTime"] - d["publishTime"]).dt.total_seconds() / 3600
    return d


def summarise(d: pd.DataFrame) -> dict:
    if d.empty:
        return {"n": 0}
    e, a = d["error"], d["actual"]
    return {
        "n": int(len(d)),
        "mae": float(e.abs().mean()),
        "rmse": float(np.sqrt((e ** 2).mean())),
        "bias": float(e.mean()),
        "wape_pct": float(e.abs().sum() / a.sum() * 100) if a.sum() else None,
        "p90_abs_error": float(e.abs().quantile(0.9)),
        "p90_shortfall": float(max(e.quantile(0.9), 0)),  # over-forecast MW exceeded only 10% of the time
        "max_abs_error": float(e.abs().max()),
        "mean_actual": float(a.mean()),
    }


def metrics(cutoff_hour: float) -> dict:
    d = joined(cutoff_hour)
    by = lambda col: [{col: k, **summarise(g)} for k, g in d.groupby(col)]
    act, fc = load_raw()
    allv = fc.merge(act, on="startTime")
    allv["error"] = allv["forecast"] - allv["actual"]
    allv["horizon_h"] = (allv["startTime"] - allv["publishTime"]).dt.total_seconds() / 3600
    allv = allv[(allv.horizon_h >= 0) & (allv.horizon_h <= 48)].copy()
    allv["bucket"] = (allv["horizon_h"] // 6 * 6).astype(int)
    horizon = [{"horizon_from_h": int(k), **summarise(g)} for k, g in allv.groupby("bucket")]
    return {"cutoff_hour": cutoff_hour, "overall": summarise(d), "by_day": by("date"),
            "by_hour": by("hour"), "by_horizon": horizon}


def day_view(date: str, cutoff_hour: float) -> dict:
    d = joined(cutoff_hour)
    g = d[d["date"] == date]
    cutoff = (pd.Timestamp(date) - pd.Timedelta(days=1) + pd.Timedelta(hours=cutoff_hour)).tz_localize(LONDON)
    series = [{"t": r.startTime.isoformat(), "forecast": r.forecast, "actual": r.actual,
               "error": r.error, "publishTime": r.publishTime.isoformat(), "horizon_h": r.horizon_h}
              for r in g.itertuples()]
    return {"date": date, "decision_cutoff": cutoff.isoformat(), "series": series, "summary": summarise(g),
            "latest_publish": g["publishTime"].max().isoformat() if len(g) else None}
