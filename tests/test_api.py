from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)


def test_health_check():
    r = client.get("/")
    assert r.status_code == 200
    assert "message" in r.json()


def test_analyze_endpoint(tmp_path):
    payload = {"symbol": "AAPL", "days": 5, "outdir": tmp_path.as_posix()}
    r = client.post("/analyze", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "report_path" in data
    assert "raw_data" in data
