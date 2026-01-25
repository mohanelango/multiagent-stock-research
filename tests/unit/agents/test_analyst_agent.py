from unittest.mock import MagicMock
from src.agents.analyst_agent import AnalystAgent
from tests.conftest import DummyChain, DummyPrompt


def test_analyst_agent_run_returns_string(sample_bundle_upper):
    agent = AnalystAgent(llm=MagicMock())

    chain = DummyChain("ANALYST_NOTE")
    agent.prompt = DummyPrompt(chain)  # key fix: avoid MagicMock with "|" operator

    out = agent.run(bundle=sample_bundle_upper, days=7)

    assert isinstance(out, str)
    assert out == "ANALYST_NOTE"
    assert chain.last_input["symbol"] == "AAPL"
    assert chain.last_input["days"] == 7
