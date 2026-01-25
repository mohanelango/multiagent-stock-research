from unittest.mock import MagicMock
from src.agents.analyst_agent import AnalystAgent
from src.agents.compliance_agent import ComplianceAgent
from src.agents.supervisor_agent import SupervisorAgent
from tests.conftest import DummyChain, DummyPrompt


def test_chain_analyst_to_compliance_to_supervisor(sample_bundle_upper):
    llm = MagicMock()

    analyst = AnalystAgent(llm)
    analyst.prompt = DummyPrompt(DummyChain("NOTE_FROM_ANALYST"))

    compliance = ComplianceAgent(llm, forbidden=["x"], disclosure=["y"])
    compliance.prompt = DummyPrompt(DummyChain("NOTE_AFTER_COMPLIANCE"))

    supervisor = SupervisorAgent(llm)
    supervisor.prompt = DummyPrompt(DummyChain("# FINAL REPORT"))

    analyst_note = analyst.run(sample_bundle_upper, days=7)
    final_note = compliance.run(analyst_note)
    report = supervisor.run(symbol="AAPL", data_summary="DATA_SUMMARY", final_note=final_note)

    assert analyst_note == "NOTE_FROM_ANALYST"
    assert final_note == "NOTE_AFTER_COMPLIANCE"
    assert report.startswith("#")
