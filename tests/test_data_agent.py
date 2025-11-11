import pytest
from unittest.mock import MagicMock, patch
from src.agents.data_agent import DataAgent


@pytest.fixture
def mock_llm():
    """Mock ChatOpenAI instance."""
    mock = MagicMock()
    mock.invoke.return_value = "Mocked LLM output"
    return mock


@pytest.fixture
def rss_templates():
    """Dummy RSS feed URLs."""
    return ["https://finance.yahoo.com/rss", "https://www.marketwatch.com/rss"]


@pytest.fixture
def mock_fmp_key():
    """Fake FMP API key."""
    return "FAKE_API_KEY"


@patch("src.agents.data_agent.fetch_price_history")
@patch("src.agents.data_agent.fetch_income_statement")
@patch("src.agents.data_agent.fetch_key_metrics")
@patch("src.agents.data_agent.fetch_news_feeds")
def test_data_agent_run(
    mock_news,
    mock_key_metrics,
    mock_income,
    mock_prices,
    mock_llm,
    rss_templates,
    mock_fmp_key,
):
    """Test DataAgent.run() end-to-end with mocked tools."""

    # Mock tool return values
    mock_prices.return_value = {"data": [{"date": "2025-01-01", "close": 150}]}
    mock_income.return_value = {"income_statement": [{"revenue": 1000}]}
    mock_key_metrics.return_value = {"key_metrics_ttm": [{"pe_ratio": 25.0}]}
    mock_news.return_value = [{"title": "Apple launches new product"}]

    # Initialize agent
    agent = DataAgent(llm=mock_llm, rss_templates=rss_templates, fmp_api_key=mock_fmp_key)

    # Run
    result = agent.run(symbol="AAPL", days=7)

    # Assertions
    assert isinstance(result, dict)
    assert result["symbol"] == "AAPL"
    assert "prices" in result
    assert "fundamentals" in result
    assert "news" in result
    assert isinstance(result["fundamentals"]["income_statement"], list)
    assert isinstance(result["fundamentals"]["key_metrics_ttm"], list)
    assert mock_prices.called
    assert mock_income.called
    assert mock_key_metrics.called
    assert mock_news.called
