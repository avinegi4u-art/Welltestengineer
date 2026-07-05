"""FastAPI route tests."""

from fastapi.testclient import TestClient

from app.main import app
from engine.benchmarks import run_engine_benchmarks

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["engine"] == "python"


def test_benchmarks_api():
    r = client.get("/api/benchmarks")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 35
    assert data["pass"] >= 33
    assert len(data["benchmarks"]) == 35


def test_benchmark_module_matches_api():
    direct = run_engine_benchmarks()
    api = client.get("/api/benchmarks").json()
    assert direct["total"] == api["total"]
    assert direct["pass"] == api["pass"]


def test_analyze_minimal():
    payload = {
        "inputs": {"analysisStepFt": 4000, "sfBurst": 1.1, "sfCollapse": 1, "sfTension": 1.2, "sfTriaxial": 1.25, "sfBuckling": 1.25},
        "state": {
            "catalog": [{"id": "P", "od": 9.625, "wt": 53.5, "grade": "L80", "conn": "BTC"}],
            "strings": [{"id": "s1", "label": "Prod", "pipeId": "P", "top": 0, "shoe": 8000, "toc": 1000, "fluidInt": 10, "fluidExt": 9}],
            "profiles": [
                {"tvd": 0, "pp": 8.6, "fg": 9.0, "mwInt": 8.6, "mwExt": 8.6, "temp": 70},
                {"tvd": 8000, "pp": 12, "fg": 15, "mwInt": 10, "mwExt": 9, "temp": 180},
            ],
        },
        "scenarios": ["production"],
    }
    r = client.post("/api/analyze", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["check_count"] > 0
    assert data["engine"] == "python"
