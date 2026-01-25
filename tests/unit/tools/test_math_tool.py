from src.tools.math_tool import basic_return_stats


def test_basic_return_stats_has_core_fields():
    closes = [100, 101, 99, 102, 105]
    stats = basic_return_stats(closes)
    print("stats---->",stats)
    assert isinstance(stats, dict)
    # be tolerant to your internal key naming
    assert "mean" in stats
    assert any(k in stats for k in ["vol", "min"])
