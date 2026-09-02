"""Unit tests for Telemetry Tokens, SDK Tokenization, and ML Training Pipeline."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.engine.tokens import create_telemetry_token, decode_telemetry_token
from app.engine.training import training_pipeline

client = TestClient(app)


def test_token_creation_and_validation():
    """Verify cryptographic token packing, signature check, and payload integrity."""
    raw_signals = {
        "flight_std_ms": 32.4,
        "dwell_mean_ms": 78.2,
        "paste_events_count": 0,
        "webdriver": False,
        "hardware_hash": "a4f91b"
    }

    token = create_telemetry_token(raw_signals, publishable_key="td_pub_test_store_1")
    assert token.startswith("td_tok_")

    is_valid, decoded, err = decode_telemetry_token(token)
    assert is_valid is True
    assert err == ""
    assert decoded["pub"] == "td_pub_test_store_1"
    assert decoded["data"]["flight_std_ms"] == 32.4


def test_token_tamper_detection():
    """Verify that tampering with token signature or payload causes verification to fail."""
    raw_signals = {"flight_std_ms": 25.0}
    token = create_telemetry_token(raw_signals)
    
    # Tamper with the payload part
    parts = token.split(".")
    tampered = parts[0] + "xyz." + parts[1]
    is_valid, _, err = decode_telemetry_token(tampered)
    assert is_valid is False
    assert "signature" in err.lower()


def test_api_tokenize_endpoint():
    """Verify POST /api/v1/telemetry/tokenize returns valid signed token."""
    payload = {
        "publishable_key": "td_pub_test_app_42",
        "signals": {
            "screen_w": 1920,
            "screen_h": 1080,
            "flight_std_ms": 36.5,
            "webdriver": False
        }
    }
    response = client.post("/api/v1/telemetry/tokenize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "telemetry_token" in data
    assert data["telemetry_token"].startswith("td_tok_")


def test_evaluate_with_telemetry_token_natural():
    """Verify risk evaluation with a natural user telemetry token yields ALLOW."""
    token = create_telemetry_token({
        "flight_std_ms": 34.0,  # Human variance
        "dwell_mean_ms": 82.0,
        "paste_events_count": 0,
        "webdriver": False
    })

    payload = {
        "user_id": "usr_token_test",
        "telemetry_token": token,
        "transaction": {"amount": 35000, "currency": "NGN"}
    }
    response = client.post("/api/v1/risk/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "allow"
    assert "valid_telemetry_token_verified" in data["reasons"]
    assert "consistent_human_typing_cadence" in data["reasons"]


def test_evaluate_with_telemetry_token_bot():
    """Verify risk evaluation with automated/headless bot token yields BLOCK."""
    token = create_telemetry_token({
        "flight_std_ms": 0.0,  # 0ms robotic cadence
        "dwell_mean_ms": 1.0,
        "paste_events_count": 3,
        "webdriver": True      # Headless automation
    })

    payload = {
        "user_id": "usr_bot_client",
        "telemetry_token": token,
        "transaction": {"amount": 250000, "currency": "NGN"}
    }
    response = client.post("/api/v1/risk/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "block"
    assert "headless_browser_automation_detected" in data["reasons"]


def test_ml_dataset_endpoint():
    """Verify GET /api/v1/ml/dataset exports collected training vectors."""
    # Ensure at least one token was scored
    test_evaluate_with_telemetry_token_natural()

    response = client.get("/api/v1/ml/dataset?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records_collected"] > 0
    records = data["records"]
    assert len(records) > 0
    first = records[0]
    assert "flight_std_ms" in first
    assert "label_decision" in first
    assert "is_anomaly" in first
