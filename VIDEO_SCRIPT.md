# Video script (≤10 min)
## Part 1 – Client pitch (≤5 min)
0:00 Problem: you buy day-ahead before knowing the wind; error = cost. 
0:40 Demo: pick a delivery day -> "forecast you'd actually have had at 09:00 on D-1" vs actual.
1:30 Slide the cut-off: show how later forecasts are better.
2:15 Accuracy: Jan MAE/RMSE/WAPE; bias (are we systematically over-forecasting?).
3:00 By-hour + horizon charts: where risk concentrates. P90 shortfall = suggested buffer in MW.
4:00 Worked example: "On day X you'd have bought N MW extra with this buffer".
4:40 Next steps: price data, probabilistic bands, alerts. Close.
## Part 2 – Tech review (≤5 min)
0:00 Architecture diagram: Elexon -> FastAPI (pandas) -> React; Docker; Heroku.
1:00 service.py: decision_forecast (cut-off, no look-ahead), tz/DST handling, metric definitions.
2:15 elexon.py: chunking, caching, pagination limits, error handling; DEMO mode only for tests.
3:00 Tests, code layout, AI usage + how I verified it.
4:00 Trade-offs & limitations (assumed gate closure, ephemeral cache, national-only).
