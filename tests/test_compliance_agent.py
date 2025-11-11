import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.agents.compliance_agent import ComplianceAgent


@pytest.fixture
def mock_llm():
    return MagicMock(name="MockLLM")


@pytest.fixture
def sample_note():
    return "Apple's recent performance is outstanding and a must-buy for all investors."


@pytest.fixture
def forbidden_terms():
    return ["must-buy", "guaranteed", "recommend"]


@pytest.fixture
def disclosure_text():
    return ["This note is for informational purposes only."]


def test_compliance_agent_run(mock_llm, sample_note, forbidden_terms, disclosure_text):
    """Ensure ComplianceAgent.run returns a valid string and invokes the chain once."""
    agent = ComplianceAgent(llm=mock_llm, forbidden=forbidden_terms, disclosure=disclosure_text)

    # Mock chain with a real string response
    mock_chain = MagicMock(name="MockChain")
    mock_chain.invoke.return_value = SimpleNamespace(
        content="Compliant Note: Apple's performance remains strong and neutral."
    )

    # Intercept prompt | llm
    class DummyPrompt:
        def __or__(self, _llm):
            return mock_chain

    agent.prompt = DummyPrompt()

    # Run
    result = agent.run(note=sample_note)

    # Assertions
    assert isinstance(result, str), f"Expected str but got {type(result)}"
    assert "Compliant Note" in result

    # Validate pipeline was used correctly
    mock_chain.invoke.assert_called_once()

    # Extract the dict argument passed positionally
    args, kwargs = mock_chain.invoke.call_args
    assert len(args) == 1, "Expected a single dict argument"
    input_dict = args[0]

    assert isinstance(input_dict, dict)
    assert "note" in input_dict
    assert "forbidden" in input_dict
    assert any(term in input_dict["forbidden"] for term in forbidden_terms)
