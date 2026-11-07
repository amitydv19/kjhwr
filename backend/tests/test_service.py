import os
os.environ["DEMO_DATA"] = "1"
from app import service


def test_no_lookahead():
    d = service.joined(9.0)
    assert len(d) > 0
    assert (d["publishTime"] <= d["cutoff"]).all()


def test_one_forecast_per_target():
    assert service.joined(9.0)["startTime"].is_unique


def test_later_cutoff_is_not_worse():
    a = service.summarise(service.joined(6.0))["mae"]
    b = service.summarise(service.joined(18.0))["mae"]
    assert b <= a * 1.05


def test_metrics_shape():
    m = service.metrics(9.0)
    assert m["overall"]["n"] > 0 and m["by_hour"] and m["by_horizon"]
