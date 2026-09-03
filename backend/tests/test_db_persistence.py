"""Tests for Database Persistence (SQLite default & PostgreSQL compatible schema)."""
import os
import pytest
from backend.app.db.session import init_db, SessionLocal, Base, engine
from backend.app.db.models import TenantDB, ApiKeyDB, TenantSettingsDB, TenantMetricsDB, DecisionAuditLogDB
from backend.app.engine.tenants import MultiTenantEngine
from backend.app.models.tenant import TenantRegisterRequest, TenantLoginRequest, CreateApiKeyRequest, TenantPolicySettings


@pytest.fixture(autouse=True)
def clean_db():
    """Recreates clean database tables for each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_tenant_db_persistence_across_engine_reboot():
    """Verifies that registered organizations and keys persist permanently to disk/db."""
    engine_1 = MultiTenantEngine()
    profile, sess_token = engine_1.register_tenant(TenantRegisterRequest(
        name="Acme Bank PLC",
        email="security@acmebank.com",
        password="securePassword123!",
        industry="Banking"
    ))

    assert profile.name == "Acme Bank PLC"
    assert len(profile.api_keys) == 1
    pub_key = profile.api_keys[0].publishable_key
    sec_key = profile.api_keys[0].secret_key

    # Simulate server reboot / new engine instance initializing
    engine_2 = MultiTenantEngine()
    
    # Fast key lookup should immediately work from reloaded DB
    match_pub = engine_2.identify_tenant_by_key(pub_key)
    match_sec = engine_2.identify_tenant_by_key(sec_key)
    assert match_pub is not None
    assert match_sec is not None
    assert match_pub[0] == profile.id
    assert match_sec[0] == profile.id

    # Profile lookup
    reloaded_profile = engine_2.get_profile(profile.id)
    assert reloaded_profile is not None
    assert reloaded_profile.email == "security@acmebank.com"
    assert reloaded_profile.industry == "Banking"


def test_api_key_lifecycle_db_persistence():
    """Verifies key creation and revocation persist in DB and key index."""
    engine = MultiTenantEngine()
    profile, _ = engine.register_tenant(TenantRegisterRequest(
        name="Fintech Corp",
        email="dev@fintechcorp.io",
        password="password123"
    ))

    # Create live key pair
    new_key = engine.create_api_key(profile.id, CreateApiKeyRequest(name="Production Gateway", environment="live"))
    assert new_key.environment == "live"
    assert new_key.publishable_key.startswith("td_pub_live_")

    # Verify key is active
    assert engine.identify_tenant_by_key(new_key.publishable_key) is not None

    # Revoke key
    revoked = engine.revoke_api_key(profile.id, new_key.id)
    assert revoked is True
    assert engine.identify_tenant_by_key(new_key.publishable_key) is None

    # Simulate reboot and verify key remains revoked
    rebooted_engine = MultiTenantEngine()
    assert rebooted_engine.identify_tenant_by_key(new_key.publishable_key) is None


def test_decision_and_metrics_db_recording():
    """Verifies evaluation decisions and audit logs persist to database."""
    engine = MultiTenantEngine()
    profile, _ = engine.register_tenant(TenantRegisterRequest(
        name="Global Remittance",
        email="ops@globalremit.com",
        password="password123"
    ))

    engine.record_decision(profile.id, {
        "customer_id": "usr_99182",
        "trust_score": 92.5,
        "decision": "ALLOW",
        "latency_ms": 0.35,
        "reasons": ["known_device", "natural_typing"],
        "amount": 450.0,
        "currency": "USD"
    })

    engine.record_decision(profile.id, {
        "customer_id": "usr_10293",
        "trust_score": 15.0,
        "decision": "BLOCK",
        "latency_ms": 0.42,
        "reasons": ["tor_exit", "impossible_travel"],
        "amount": 25000.0,
        "currency": "USD"
    })

    # Retrieve audit logs
    logs = engine.get_tenant_audit_logs(profile.id, limit=10)
    assert len(logs) == 2
    assert logs[0]["customer_id"] == "usr_10293"
    assert logs[0]["decision"] == "BLOCK"
    assert logs[1]["customer_id"] == "usr_99182"
    assert logs[1]["decision"] == "ALLOW"

    # Verify updated profile metrics
    updated_profile = engine.get_profile(profile.id)
    assert updated_profile.metrics.total_evaluations == 2
    assert updated_profile.metrics.allow_count == 1
    assert updated_profile.metrics.block_count == 1
