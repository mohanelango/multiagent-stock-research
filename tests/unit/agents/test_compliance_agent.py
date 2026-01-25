from unittest.mock import MagicMock
from src.agents.compliance_agent import ComplianceAgent
from tests.conftest import DummyChain, DummyPrompt


def test_compliance_agent_run_returns_string():
    agent = ComplianceAgent(
        llm=MagicMock(),
        forbidden=["guaranteed returns"],
        disclosure=["not advice"]
    )

    chain = DummyChain("FINAL_NOTE")
    agent.prompt = DummyPrompt(chain)

    out = agent.run("some note")
    assert out == "FINAL_NOTE"
    assert chain.last_input["note"] == "some note"
    assert "forbidden" in chain.last_input
