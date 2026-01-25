from unittest.mock import MagicMock
from src.agents.supervisor_agent import SupervisorAgent
from tests.conftest import DummyChain, DummyPrompt


def test_supervisor_agent_run_returns_string():
    agent = SupervisorAgent(llm=MagicMock())

    chain = DummyChain("# MARKDOWN REPORT")
    agent.prompt = DummyPrompt(chain)

    out = agent.run(symbol="AAPL", data_summary="DATA", final_note="NOTE")
    assert isinstance(out, str)
    assert out.startswith("#")
    assert chain.last_input["symbol"] == "AAPL"
