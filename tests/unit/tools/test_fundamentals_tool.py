from types import SimpleNamespace
from src.tools.fundamentals_tool import fetch_income_statement, fetch_key_metrics


def test_fundamentals_tools_do_not_raise_on_payment_errors(monkeypatch):
    # Mock requests.get if your tools use requests
    def fake_get(*_args, **_kwargs):
        return SimpleNamespace(status_code=402, text="Payment Required", json=lambda: {"error": "Payment Required"})

    try:
        monkeypatch.setattr("src.tools.fundamentals_tool.requests.get", fake_get)
    except Exception:
        # If you don't use requests, skip this monkeypatch and still run the "no crash" contract.
        pass

    inc = fetch_income_statement("AAPL", api_key="demo", limit=2)
    km = fetch_key_metrics("AAPL", api_key="demo")

    assert isinstance(inc, dict)
    assert isinstance(km, dict)
    # Contract: must not throw; either returns empty lists or includes an error object.
    assert ("income_statement" in inc) or ("__error__" in inc) or (inc == {})
    assert ("key_metrics_ttm" in km) or ("__error__" in km) or (km == {})
