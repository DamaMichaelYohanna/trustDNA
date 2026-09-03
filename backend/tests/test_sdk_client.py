"""Test official Python SDK client integration."""
import pytest
from sdk.python.trustdna import TrustDNAClient, AuthenticationError
from backend.app.main import app
from fastapi.testclient import TestClient

test_client = TestClient(app)


def test_python_sdk_initialization():
    """Confirms SDK validates secret key requirement."""
    with pytest.raises(AuthenticationError):
        TrustDNAClient(secret_key="")


def test_python_sdk_risk_evaluation_mock(monkeypatch):
    """Tests evaluating risk using the Python SDK client."""
    # First register a real tenant to obtain a valid secret key
    reg_res = test_client.post("/api/v1/auth/register", json={
        "name": "SDK Test Org",
        "email": "sdk@testorg.com",
        "password": "sdkpassword123",
        "industry": "Fintech & Payments"
    })
    assert reg_res.status_code == 200
    tenant = reg_res.json()["tenant"]
    sec_key = tenant["api_keys"][0]["secret_key"]

    client = TrustDNAClient(secret_key=sec_key, base_url="http://testserver/api/v1")

    # Mock session.post to route through TestClient
    def mock_post(url, json=None, timeout=None):
        endpoint = url.replace("http://testserver/api/v1", "/api/v1")
        return test_client.post(endpoint, json=json, headers={"Authorization": f"Bearer {sec_key}"})

    monkeypatch.setattr(client.session, "post", mock_post)

    decision = client.risk.evaluate(
        customer_id="usr_sdk_001",
        amount=500.0,
        currency="USD"
    )

    assert decision.customer_id == "usr_sdk_001"
    assert decision.decision in ["allow", "challenge", "block"]
    assert decision.trust_score >= 0.0
    assert decision.subscores.device_health >= 0.0
