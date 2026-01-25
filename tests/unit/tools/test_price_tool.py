from src.tools.price_tool import fetch_price_history


def test_price_tool_returns_dict(monkeypatch):
    # Patch yfinance usage if present
    try:
        monkeypatch.setattr("src.tools.price_tool.yf.download", lambda *a, **k: [])
    except Exception:
        pass

    out = fetch_price_history("AAPL", 5)
    assert isinstance(out, dict)
