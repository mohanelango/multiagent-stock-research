import os
from src.tools.price_tool import fetch_price_history
from src.tools.math_tool import basic_return_stats

def test_price_tool_basic():
    out = fetch_price_history("AAPL", days=5)
    assert "data" in out
    assert out["symbol"] == "AAPL"

def test_math_tool_stats():
    stats = basic_return_stats([100, 101, 99, 100])
    assert stats["count"] == 3
