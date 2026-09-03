"""Tests for Deterministic Developer QA Test Tokens and Outbound Signed Webhooks."""
import json
import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.engine.tokens import decode_telemetry_token
from backend.app.engine.webhooks import generate_webhook_signature, dispatch_webhook_event
from backend.app.engine.tenants import MultiTenantEngine
from backend.app.models.tenant import TenantRegisterRequest, TenantPolicySettings
from backend.app.db.session import init_db, Base, engine

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_deterministic_qa_tokens_decoding():
    """Verifies that deterministic test tokens decode reliably for automated testing."""
    for tok in ["td_tok_test_allow", "td_tok_test_challenge", "td_tok_test_block"]:
        valid, payload, err = decode_telemetry_token(tok)
        assert valid is True
        assert err == ""
        assert "data" in payload
        assert "device" in payload["data"]


def test_evaluate_with_qa_tokens_full_pipeline():
    """Tests evaluate endpoint with each deterministic developer QA test token."""
    # 1. ALLOW Token
    res_allow = client.post("/api/v1/risk/evaluate", json={
        "customer_id": "usr_qa_1",
        "telemetry_token": "td_tok_test_allow",
        "transaction": {"amount": 50.0, "currency": "USD"}
    })
    assert res_allow.status_code == 200
    data_allow = res_allow.json()
    assert data_allow["decision"] == "allow"
    assert data_allow["trust_score"] >= 75

    # 2. CHALLENGE Token
    res_challenge = client.post("/api/v1/risk/evaluate", json={
        "customer_id": "usr_qa_2",
        "telemetry_token": "td_tok_test_challenge",
        "transaction": {"amount": 500.0, "currency": "USD"}
    })
    assert res_challenge.status_code == 200
    data_challenge = res_challenge.json()
    assert data_challenge["decision"] == "challenge"
    assert 40 <= data_challenge["trust_score"] < 75

    # 3. BLOCK Token
    res_block = client.post("/api/v1/risk/evaluate", json={
        "customer_id": "usr_qa_3",
        "telemetry_token": "td_tok_test_block",
        "transaction": {"amount": 25000.0, "currency": "USD"}
    })
    assert res_block.status_code == 200
    data_block = res_block.json()
    assert data_block["decision"] == "block"
    assert data_block["trust_score"] < 40


def test_webhook_signature_generation():
    """Verifies HMAC-SHA256 signature format: t=<timestamp>,v1=<hash>."""
    ts = 1756891200
    payload = json.dumps({"event": "risk.blocked", "score": 12})
    secret = "whsec_test_secret_key_123"

    sig_header = generate_webhook_signature(payload, secret, ts)
    assert sig_header.startswith(f"t={ts},v1=")
    sig_hex = sig_header.split(",v1=")[1]
    assert len(sig_hex) == 64  # SHA-256 hex string


@patch("requests.post")
def test_webhook_dispatch_on_risk_evaluation(mock_post):
    """Verifies that an outbound signed webhook is triggered when a tenant has a configured webhook_url."""
    mock_post.return_value = MagicMock(status_code=200)

    # 1. Register tenant and configure webhook endpoint
    reg_res = client.post("/api/v1/auth/register", json={
        "name": "Webhook Tester Corp",
        "email": "wh@testcorp.com",
        "password": "password123"
    })
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    tenant_id = reg_data["tenant"]["id"]
    sec_key = reg_data["tenant"]["api_keys"][0]["secret_key"]

    # Update tenant settings with webhook URL
    set_res = client.put(f"/api/v1/tenant/{tenant_id}/settings", json={
        "allow_threshold": 70,
        "mfa_threshold": 40,
        "block_threshold": 39,
        "impossible_travel_enabled": True,
        "bot_cadence_enabled": True,
        "touch_biometrics_enabled": True,
        "velocity_spike_enabled": True,
        "webhook_url": "https://api.testcorp.com/v1/trustdna-webhook",
        "webhook_secret": "whsec_custom_corp_key"
    })
    assert set_res.status_code == 200

    # 2. Trigger risk evaluation with tenant's secret key
    eval_res = client.post(
        "/api/v1/risk/evaluate",
        headers={"Authorization": f"Bearer {sec_key}"},
        json={
            "customer_id": "usr_flagged_1",
            "telemetry_token": "td_tok_test_block",
            "transaction": {"amount": 8000.0, "currency": "USD"}
        }
    )
    assert eval_res.status_code == 200
    assert eval_res.json()["decision"] == "block"

    # 3. Verify webhook was dispatched
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[0][0] == "https://api.testcorp.com/v1/trustdna-webhook"
    headers = call_args[1]["headers"]
    assert headers["X-TrustDNA-Event"] == "risk.block"
    assert "X-TrustDNA-Signature" in headers
    assert headers["X-TrustDNA-Signature"].startswith("t=")
