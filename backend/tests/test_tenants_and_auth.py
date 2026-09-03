"""Unit and integration tests for multi-tenant management, authentication, and key lifecycle."""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.engine.tenants import tenant_engine

client = TestClient(app)


def test_tenant_registration_and_listing():
    """Tests registering a new client organization and listing it."""
    email = "admin@hyperpay.io"
    res = client.post("/api/v1/auth/register", json={
        "name": "HyperPay International",
        "email": email,
        "password": "SuperSecretPassword123",
        "industry": "Fintech & Payments"
    })
    assert res.status_code == 200
    data = res.json()
    assert "session_token" in data
    tenant = data["tenant"]
    assert tenant["name"] == "HyperPay International"
    assert tenant["email"] == email
    assert len(tenant["api_keys"]) == 1
    assert tenant["api_keys"][0]["publishable_key"].startswith("td_pub_test_")
    assert tenant["api_keys"][0]["secret_key"].startswith("td_sec_test_")

    # Verify listing contains the registered tenant
    list_res = client.get("/api/v1/auth/tenants")
    assert list_res.status_code == 200
    names = [t["name"] for t in list_res.json()]
    assert "HyperPay International" in names

    # Duplicate registration should fail
    dup_res = client.post("/api/v1/auth/register", json={
        "name": "HyperPay Duplicate",
        "email": email,
        "password": "AnotherPassword",
        "industry": "Fintech"
    })
    assert dup_res.status_code == 400


def test_tenant_login_flow():
    """Tests client login authentication."""
    email = "ops@stellarvault.com"
    # Register first
    reg_res = client.post("/api/v1/auth/register", json={
        "name": "Stellar Vault",
        "email": email,
        "password": "securepassword456",
        "industry": "Crypto & Digital Assets"
    })
    assert reg_res.status_code == 200

    # Test valid login
    res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "securepassword456"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["tenant"]["name"] == "Stellar Vault"
    assert "session_token" in data

    # Test invalid password
    bad_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "wrongpassword"
    })
    assert bad_res.status_code == 401


def test_api_key_creation_and_revocation():
    """Tests creating additional key pairs and revoking existing ones."""
    email = "lead@orbitpay.net"
    reg_res = client.post("/api/v1/auth/register", json={
        "name": "OrbitPay Network",
        "email": email,
        "password": "orbitpassword123",
        "industry": "Neobanking & Wallet"
    })
    assert reg_res.status_code == 200
    tenant_id = reg_res.json()["tenant"]["id"]
    
    # Generate new Live API key
    res = client.post(f"/api/v1/tenant/{tenant_id}/keys", json={
        "name": "Production Mobile Key",
        "environment": "live"
    })
    assert res.status_code == 200
    new_key = res.json()
    assert new_key["name"] == "Production Mobile Key"
    assert new_key["publishable_key"].startswith("td_pub_live_")
    assert new_key["secret_key"].startswith("td_sec_live_")
    assert new_key["status"] == "active"

    # Verify key shows up in tenant keys list
    keys_res = client.get(f"/api/v1/tenant/{tenant_id}/keys")
    assert keys_res.status_code == 200
    keys_list = keys_res.json()
    assert any(k["id"] == new_key["id"] for k in keys_list)

    # Revoke key
    revoke_res = client.post(f"/api/v1/tenant/{tenant_id}/keys/{new_key['id']}/revoke")
    assert revoke_res.status_code == 200
    assert revoke_res.json()["status"] == "revoked"

    # Verify key status is revoked in profile
    profile_res = client.get(f"/api/v1/tenant/{tenant_id}/profile")
    revoked_match = next(k for k in profile_res.json()["api_keys"] if k["id"] == new_key["id"])
    assert revoked_match["status"] == "revoked"


def test_risk_evaluation_tenant_attribution():
    """Tests that evaluating risk with a tenant secret key increments tenant metrics and logs."""
    email = "dev@zenithflow.io"
    reg_res = client.post("/api/v1/auth/register", json={
        "name": "ZenithFlow",
        "email": email,
        "password": "zenithpassword123",
        "industry": "E-Commerce & Retail"
    })
    assert reg_res.status_code == 200
    tenant_data = reg_res.json()["tenant"]
    tenant_id = tenant_data["id"]
    sec_key = tenant_data["api_keys"][0]["secret_key"]
    initial_evals = tenant_data["metrics"]["total_evaluations"]

    # Send evaluation with ZenithFlow's secret key
    payload = {
        "customer_id": "usr_zf_test_1",
        "device": {
            "device_id": "dev_zf_01",
            "screen_resolution": "1920x1080",
            "is_headless": False
        },
        "behavior": {
            "dwell_time_mean_ms": 110.0,
            "flight_time_mean_ms": 140.0
        },
        "transaction": {
            "amount": 250.0,
            "currency": "USD",
            "is_first_time_user": False
        }
    }

    eval_res = client.post(
        "/api/v1/risk/evaluate",
        json=payload,
        headers={"Authorization": f"Bearer {sec_key}"}
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["decision"].lower() in ["allow", "challenge", "block"]

    # Check updated tenant metrics
    profile_after = client.get(f"/api/v1/tenant/{tenant_id}/profile").json()
    assert profile_after["metrics"]["total_evaluations"] == initial_evals + 1

    # Check tenant audit log
    logs_res = client.get(f"/api/v1/tenant/{tenant_id}/audit-logs")
    assert logs_res.status_code == 200
    logs = logs_res.json()["logs"]
    assert len(logs) > 0
    assert logs[0]["customer_id"] == "usr_zf_test_1"
    assert logs[0]["amount"] == 250.0


def test_tenant_policy_settings_update():
    """Tests updating tenant custom risk thresholds."""
    email = "policy@pulseguard.org"
    reg_res = client.post("/api/v1/auth/register", json={
        "name": "PulseGuard Health",
        "email": email,
        "password": "guardpassword123",
        "industry": "Healthcare & Telemedicine"
    })
    assert reg_res.status_code == 200
    tenant_id = reg_res.json()["tenant"]["id"]

    update_payload = {
        "allow_threshold": 80,
        "mfa_threshold": 50,
        "block_threshold": 49,
        "impossible_travel_enabled": True,
        "bot_cadence_enabled": True,
        "touch_biometrics_enabled": False,
        "velocity_spike_enabled": True
    }
    res = client.put(f"/api/v1/tenant/{tenant_id}/settings", json=update_payload)
    assert res.status_code == 200
    settings = res.json()
    assert settings["allow_threshold"] == 80
    assert settings["mfa_threshold"] == 50
    assert settings["touch_biometrics_enabled"] is False
