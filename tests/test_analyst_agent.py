import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.agents.analyst_agent import AnalystAgent


@pytest.fixture
def sample_bundle():
    return {
        "symbol": "AAPL",
        "prices": {"data": [
            {"date": "2025-01-01", "close": 150},
            {"date": "2025-01-02", "close": 152},
            {"date": "2025-01-03", "close": 151},
            {"date": "2025-01-04", "close": 153},
            {"date": "2025-01-05", "close": 154},
        ]},
        "fundamentals": {
            "income_statement": [{"revenue": 1000, "net_income": 200}],
            "key_metrics_ttm": [{"pe_ratio": 25}],
        },
        "news": [
            {"title": "Apple launches AI-powered iPhone"},
            {"title": "Apple posts record quarterly results"},
            {"title": "Apple expands services business"},
        ],
    }


def test_analyst_agent_run(sample_bundle):
    """
    Ensure AnalystAgent.run returns a real string by controlling the pipe (prompt | llm)
    from the prompt side. We inject a DummyPrompt whose __or__ returns a mock chain.
    """
    mock_llm = MagicMock(name="MockLLM")

    agent = AnalystAgent(llm=mock_llm)

    # Prepare a mock chain that returns a real object with .content (not a MagicMock)
    mock_chain = MagicMock(name="MockChain")
    mock_chain.invoke.return_value = SimpleNamespace(
        content="Mocked Analyst Note: Apple fundamentals remain resilient with steady price action."
    )

    # Replace the agent's prompt with a DummyPrompt that pipes to our mock_chain
    class DummyPrompt:
        def __or__(self, _llm):
            return mock_chain

    agent.prompt = DummyPrompt()

    result = agent.run(bundle=sample_bundle, days=7)

    assert isinstance(result, str), f"Expected str but got {type(result)}"
    assert "Mocked Analyst Note" in result
    mock_chain.invoke.assert_called_once()
