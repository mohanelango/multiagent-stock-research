from fastapi.testclient import TestClient
import src.api as api_module


def test_api_analyze_contract(monkeypatch, tmp_path):
    # Patch run_pipeline so API test is stable and offline
    def fake_run_pipeline(symbol, days, outdir, human=False):
        out = tmp_path / symbol
        out.mkdir(exist_ok=True)
        return {
            "report": str(out / "r.md"),
            "plot": str(out / "c.png"),
            "raw": str(out / "d.json"),
            "pdf": str(out / "r.pdf"),
        }

    monkeypatch.setattr(api_module, "run_pipeline", fake_run_pipeline)

    client = TestClient(api_module.app)
    r = client.post("/analyze", json={"symbol": "AAPL", "days": 5})

    assert r.status_code == 200
    body = r.json()
    print("---24-----",body)
    # Contract: always return paths
    assert "report_path" in body
    assert "plot_path" in body
    assert "raw_data" in body
    assert "pdf_path" in body
