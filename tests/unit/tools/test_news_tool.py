from src.tools.news_tool import fetch_news_feeds


def test_fetch_news_feeds_handles_empty_gracefully(monkeypatch):
    # If your implementation uses feedparser, patch it; if it uses requests, patch that instead.
    # This test is intentionally tolerant: it asserts "no crash" and list output.
    try:
        monkeypatch.setattr("src.tools.news_tool.feedparser.parse", lambda *_args, **_kwargs: type("X", (), {"entries": []})())
    except Exception:
        pass

    out = fetch_news_feeds("AAPL", ["https://example.com/rss"], max_items=5)
    assert isinstance(out, list)
