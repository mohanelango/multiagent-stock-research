import pytest
from fastapi.testclient import TestClient
from src.api import app


@pytest.fixture(scope="session")
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture(scope="session")
def sample_symbol():
    return "AAPL"


@pytest.fixture(scope="session")
def sample_days():
    return 30
