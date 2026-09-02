"""Comprehensive unit and integration test suite for TrustDNA Risk Engine."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.engine.scorer import evaluate_risk
from app.engine.travel import calculate_haversine_distance, calculate_travel_velocity
from app.engine.velocity import VelocityTracker
from app.models.request import (
    RiskEvaluationRequest,
    DeviceTelemetry,
    NetworkTelemetry,
    TravelTelemetry,
    BehaviorTelemetry,
    TransactionTelemetry,
)

client = TestClient(app)


def test_legitimate_scenario():
    """Legitimate user with trusted device, clean residential IP, natural behavior, and normal amount."""
    req = RiskEvaluationRequest(
        user_id="usr_legit_001",
        device=DeviceTelemetry(profile="known_trusted"),
        network=NetworkTelemetry(type="residential"),
        travel=TravelTelemetry(distance_km=0),
        behavior=BehaviorTelemetry(typing_profile="natural"),
        transaction=TransactionTelemetry(amount=45000)
    )
    res = evaluate_risk(req)
    assert res.decision == "allow"
    assert res.trust_score >= 75
    assert res.risk_level == "low"
    assert res.recommended_action == "proceed"
    assert "known_device_profile" in res.reasons
    assert "residential_ip_clean" in res.reasons


def test_suspicious_scenario():
    """Suspicious scenario: new fingerprint, commercial VPN, deviated typing cadence, moderate spend."""
    req = RiskEvaluationRequest(
        user_id="usr_suspicious_002",
        device=DeviceTelemetry(profile="new_fingerprint"),
        network=NetworkTelemetry(type="datacenter_vpn"),
        travel=TravelTelemetry(distance_km=450),
        behavior=BehaviorTelemetry(typing_profile="deviated"),
        transaction=TransactionTelemetry(amount=650000)
    )
    res = evaluate_risk(req)
    assert res.decision == "challenge"
    assert 40 <= res.trust_score < 75
    assert res.risk_level == "medium"
    assert res.recommended_action == "require_totp_mfa"


def test_attack_scenario():
    """Attack scenario: rooted/emulated, Tor exit node, robotic cadence, impossible travel (3,200 km), high amount."""
    req = RiskEvaluationRequest(
        user_id="usr_attacker_003",
        device=DeviceTelemetry(profile="emulated_rooted"),
        network=NetworkTelemetry(type="tor_exit"),
        travel=TravelTelemetry(distance_km=3200),
        behavior=BehaviorTelemetry(typing_profile="robotic_paste"),
        transaction=TransactionTelemetry(amount=4500000)
    )
    res = evaluate_risk(req)
    assert res.decision == "block"
    assert res.trust_score < 40
    assert res.risk_level == "high"
    assert res.recommended_action == "block_and_terminate_session"
    assert "tor_anonymizing_exit_node" in res.reasons
    assert "emulated_or_rooted_environment" in res.reasons


def test_haversine_distance_and_velocity():
    """Verify distance and impossible travel calculations."""
    # Lagos (6.5244, 3.3792) to Abuja (9.0765, 7.3986): ~535 km
    dist = calculate_haversine_distance(6.5244, 3.3792, 9.0765, 7.3986)
    assert 500 < dist < 580

    # If covered in 0.2 hours (12 minutes) -> velocity > 2600 km/h -> impossible!
    vel, is_impossible = calculate_travel_velocity(dist, 0.2)
    assert is_impossible is True
    assert vel > 800.0

    # If covered in 6 hours -> velocity ~90 km/h -> plausible
    vel_normal, is_impossible_normal = calculate_travel_velocity(dist, 6.0)
    assert is_impossible_normal is False
    assert vel_normal < 200.0


def test_velocity_tracker_sliding_window():
    """Verify in-memory sliding window counting."""
    tracker = VelocityTracker()
    entity = "card_12345"

    t0 = 1000.0
    tracker.record_attempt(entity, timestamp=t0)
    tracker.record_attempt(entity, timestamp=t0 + 10)
    tracker.record_attempt(entity, timestamp=t0 + 20)

    # Within 60 seconds of t0 + 20
    count = tracker.get_velocity_count(entity, window_seconds=60.0, current_time=t0 + 25)
    assert count == 3

    # After 65 seconds from t0 (cutoff = 1005), only t0 has expired; t0+10 and t0+20 remain
    count_later = tracker.get_velocity_count(entity, window_seconds=60.0, current_time=t0 + 65)
    assert count_later == 2

    # After 85 seconds from t0 (cutoff = 1025), all attempts have expired
    count_expired = tracker.get_velocity_count(entity, window_seconds=60.0, current_time=t0 + 85)
    assert count_expired == 0


def test_api_health_endpoint():
    """Verify GET /api/v1/health."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "TrustDNA" in data["engine"]


def test_api_risk_evaluate_endpoint():
    """Verify POST /api/v1/risk/evaluate endpoint returns 200 and schema matches."""
    payload = {
        "user_id": "usr_web_client",
        "device": {"profile": "known_trusted"},
        "network": {"type": "residential"},
        "travel": {"distance_km": 0},
        "behavior": {"typing_profile": "natural"},
        "transaction": {"amount": 50000, "currency": "NGN"}
    }
    response = client.post("/api/v1/risk/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "allow"
    assert "trust_score" in data
    assert "latency_ms" in data
    assert data["latency_ms"] < 50.0  # Ultra-low latency guarantee


def test_api_keys_generate_endpoint():
    """Verify POST /api/v1/keys/generate returns sandbox key pair."""
    payload = {"app_name": "Fintech Demo App", "environment": "sandbox"}
    response = client.post("/api/v1/keys/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["publishable_key"].startswith("td_pub_test_")
    assert data["secret_key"].startswith("td_sec_test_")


def test_observability_middleware_headers():
    """Verify X-Request-ID and Server-Timing W3C headers are present on every response."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "Server-Timing" in response.headers
    assert "total;dur=" in response.headers["Server-Timing"]


def test_background_audit_logging():
    """Verify evaluations write to async audit log out-of-band without blocking response."""
    payload = {
        "user_id": "usr_audit_test",
        "device": {"profile": "known_trusted"},
        "network": {"type": "residential"},
        "travel": {"distance_km": 0},
        "behavior": {"typing_profile": "natural"},
        "transaction": {"amount": 12000, "currency": "NGN"}
    }
    eval_resp = client.post("/api/v1/risk/evaluate", json=payload)
    assert eval_resp.status_code == 200

    # Inspect audit trail endpoint
    audit_resp = client.get("/api/v1/audit/recent?limit=10")
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()
    assert audit_data["count"] > 0
    records = audit_data["records"]
    assert any(r["customer_id"] == "usr_audit_test" for r in records)


def test_in_memory_eviction_and_memory_leak_prevention():
    """Verify expired entities are deleted from memory and capacity limit evicts oldest keys."""
    tracker = VelocityTracker(max_entities=5)
    
    # 1. Test active entity cleanup when drained
    tracker.record_attempt("temp_entity", timestamp=100.0)
    assert tracker.active_entities_count == 1
    # Count after window has elapsed (cutoff = 170 > 100)
    count = tracker.get_velocity_count("temp_entity", window_seconds=60.0, current_time=170.0)
    assert count == 0
    # Entity key should be evicted from memory to avoid RAM leakage
    assert tracker.active_entities_count == 0

    # 2. Test hard capacity bound
    for i in range(10):
        tracker.record_attempt(f"user_{i}", timestamp=200.0 + i)
    
    # Should not exceed maximum capacity limit of 5
    assert tracker.active_entities_count <= 5
