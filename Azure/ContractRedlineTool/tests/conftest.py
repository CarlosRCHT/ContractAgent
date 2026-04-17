import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_recommendation():
    return {
        "original_text": "unlimited liability",
        "replacement_text": "liability not to exceed the total contract value",
        "rationale": "Prohibited term per procurement policy §4.2",
        "risk_level": "major",
        "section": "Limitation of Liability",
    }


@pytest.fixture
def sample_request(sample_recommendation):
    return {
        "document_url": "https://contoso.sharepoint.com/sites/contracts/Shared Documents/test.docx",
        "recommendations": [sample_recommendation],
        "author": "Test Agent",
    }
