import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.agents.supervisor_agent import SupervisorAgent


@pytest.fixture
def mock_llm():
    """Return a mock LLM."""
    return MagicMock(name="MockLLM")


@pytest.fixture
def sample_inputs():
    """Provide realistic test data."""
    return {
        "symbol": "AAPL",
        "data_summary": "Apple's revenue rose 5% YoY, net income stable, strong cash reserves.",
        "final_note": "Compliant Note: Apple maintains a balanced outlook with steady growth momentum."
    }


def test_supervisor_agent_run(mock_llm, sample_inputs):
    """Ensure SupervisorAgent.run produces a valid markdown string and invokes LLM once."""
    agent = SupervisorAgent(llm=mock_llm)

    # Mock the LangChain chain
    mock_chain = MagicMock(name="MockChain")
    mock_chain.invoke.return_value = SimpleNamespace(
        content="# Apple (AAPL)\n\n**Summary:** Revenue up 5% YoY.\n\n**Analyst Note:** Balanced growth outlook.\n\n**Sources:** Internal data."
    )

    # DummyPrompt to intercept the pipe (prompt | llm)
    class DummyPrompt:
        def __or__(self, _llm):
            return mock_chain

    # Inject dummy prompt
    agent.prompt = DummyPrompt()

    # Run
    result = agent.run(
        symbol=sample_inputs["symbol"],
        data_summary=sample_inputs["data_summary"],
        final_note=sample_inputs["final_note"]
    )

    # Assertions
    assert isinstance(result, str), f"Expected str but got {type(result)}"
    assert result.startswith("# "), "Output should look like markdown report"
    assert "Summary" in result or "Analyst Note" in result

    # Verify the chain was called once and correctly
    mock_chain.invoke.assert_called_once()
    args, kwargs = mock_chain.invoke.call_args
    assert len(args) == 1, "Expected a single positional dict argument"
    input_dict = args[0]

    assert input_dict["symbol"] == sample_inputs["symbol"]
    assert "data_summary" in input_dict
    assert "final_note" in input_dict
    assert isinstance(input_dict["data_summary"], str)
    assert isinstance(input_dict["final_note"], str)
