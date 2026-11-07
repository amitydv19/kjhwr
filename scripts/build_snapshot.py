"""Run ONCE locally (needs internet): downloads Jan 2026 data from Elexon into backend/data/*.csv.gz.
Commit those files so Vercel serves instantly without calling Elexon.
Usage: cd backend && python ../scripts/build_snapshot.py"""
import sys, os
from pathlib import Path
sys.path.insert(0, os.getcwd())
os.environ.pop("DEMO_DATA", None)
from app import elexon, service
from datetime import timedelta

DATA = Path("data"); DATA.mkdir(exist_ok=True)
# bypass snapshot while building
import shutil
for f in DATA.glob("*.csv.gz"): f.unlink()
a = elexon.fetch_actuals(service.DECISION_START + timedelta(days=1), service.DECISION_END + timedelta(days=1))
f = elexon.fetch_forecasts(service.DECISION_START, service.DECISION_END)
a.to_csv(DATA / "actuals.csv.gz", index=False)
f.to_csv(DATA / "forecasts.csv.gz", index=False)
print("actuals", a.shape, a.startTime.min(), a.startTime.max())
print("forecasts", f.shape, f.publishTime.min(), f.publishTime.max())
