"""Multi-Tenant Store and Account Management Engine for TrustDNA.
Backed by SQLAlchemy ORM (SQLite / PostgreSQL) with high-speed in-memory key cache.
"""
import hashlib
import json
import secrets
import time
import threading
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from ..db.session import init_db, SessionLocal
from ..db.models import (
    TenantDB,
    ApiKeyDB,
    TenantSettingsDB,
    TenantMetricsDB,
    DecisionAuditLogDB
)
from ..models.tenant import (
    ApiKeyModel,
    TenantPolicySettings,
    TenantMetrics,
    TenantRegisterRequest,
    TenantLoginRequest,
    CreateApiKeyRequest,
    TenantProfile,
    TenantSummary
)


def _hash_password(password: str, salt: str = "trustdna_salt_v1") -> str:
    """Computes secure SHA-256 hash of password with salt."""
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


class MultiTenantEngine:
    def __init__(self):
        self._lock = threading.RLock()
        # Fast in-memory cache for ultra-fast critical evaluation path (< 0.01ms)
        self.key_index: Dict[str, Tuple[str, str]] = {}  # key_str -> (tenant_id, key_id)
        self.settings_cache: Dict[str, TenantPolicySettings] = {}  # tenant_id -> settings
        
        # Ensure schema tables exist
        init_db()
        self._load_cache_from_db()

    def _load_cache_from_db(self):
        """Loads active API keys and policy settings into memory on boot."""
        with self._lock:
            with SessionLocal() as db:
                tenants = db.query(TenantDB).all()
                for t in tenants:
                    if t.settings:
                        self.settings_cache[t.id] = TenantPolicySettings(
                            allow_threshold=t.settings.allow_threshold,
                            mfa_threshold=t.settings.mfa_threshold,
                            block_threshold=t.settings.block_threshold,
                            impossible_travel_enabled=t.settings.impossible_travel_enabled,
                            bot_cadence_enabled=t.settings.bot_cadence_enabled,
                            touch_biometrics_enabled=t.settings.touch_biometrics_enabled,
                            velocity_spike_enabled=t.settings.velocity_spike_enabled,
                            webhook_url=t.settings.webhook_url,
                            webhook_secret=t.settings.webhook_secret
                        )
                    for k in t.api_keys:
                        if k.status == "active":
                            self.key_index[k.publishable_key] = (t.id, k.id)
                            self.key_index[k.secret_key] = (t.id, k.id)

    def register_tenant(self, req: TenantRegisterRequest) -> Tuple[TenantProfile, str]:
        """Registers a new organization in database and generates default keys."""
        email_clean = req.email.strip().lower()
        now = time.time()
        tenant_id = f"org_{secrets.token_hex(6)}"
        key_id = f"key_{secrets.token_hex(6)}"
        pub_key = f"td_pub_test_{secrets.token_hex(8)}"
        sec_key = f"td_sec_test_{secrets.token_hex(16)}"

        with self._lock:
            with SessionLocal() as db:
                existing = db.query(TenantDB).filter(TenantDB.email == email_clean).first()
                if existing:
                    raise ValueError("An organization with this email address already exists.")

                new_tenant = TenantDB(
                    id=tenant_id,
                    name=req.name.strip(),
                    email=email_clean,
                    password_hash=_hash_password(req.password),
                    industry=req.industry.strip(),
                    plan="Scale",
                    created_at_epoch=now
                )

                default_key = ApiKeyDB(
                    id=key_id,
                    tenant_id=tenant_id,
                    name="Primary Sandbox Key",
                    publishable_key=pub_key,
                    secret_key=sec_key,
                    environment="sandbox",
                    created_at_epoch=now,
                    status="active"
                )

                default_settings = TenantSettingsDB(tenant_id=tenant_id)
                default_metrics = TenantMetricsDB(tenant_id=tenant_id)

                db.add(new_tenant)
                db.add(default_key)
                db.add(default_settings)
                db.add(default_metrics)
                db.commit()

                # Sync to fast in-memory cache
                self.key_index[pub_key] = (tenant_id, key_id)
                self.key_index[sec_key] = (tenant_id, key_id)
                self.settings_cache[tenant_id] = TenantPolicySettings()

            session_token = f"td_sess_{tenant_id}_{secrets.token_hex(16)}"
            profile = self.get_profile(tenant_id)
            if not profile:
                raise ValueError("Failed to retrieve newly created tenant profile.")
            return profile, session_token

    def authenticate(self, req: TenantLoginRequest) -> Tuple[TenantProfile, str]:
        """Authenticates a tenant with email and password."""
        email_clean = req.email.strip().lower()
        with SessionLocal() as db:
            tenant = db.query(TenantDB).filter(TenantDB.email == email_clean).first()
            if not tenant or tenant.password_hash != _hash_password(req.password):
                raise ValueError("Invalid email or password.")
            
            tenant_id = tenant.id

        session_token = f"td_sess_{tenant_id}_{secrets.token_hex(16)}"
        profile = self.get_profile(tenant_id)
        if not profile:
            raise ValueError("Failed to load tenant profile.")
        return profile, session_token

    def list_all_tenants(self) -> List[TenantSummary]:
        """Returns summary list of all registered client organizations."""
        with SessionLocal() as db:
            tenants = db.query(TenantDB).all()
            summaries = []
            for t in tenants:
                active_count = sum(1 for k in t.api_keys if k.status == "active")
                total_evals = t.metrics.total_evaluations if t.metrics else 0
                summaries.append(TenantSummary(
                    id=t.id,
                    name=t.name,
                    email=t.email,
                    industry=t.industry,
                    active_keys_count=active_count,
                    total_evaluations=total_evals
                ))
            return summaries

    def get_profile(self, tenant_id: str) -> Optional[TenantProfile]:
        """Fetches complete profile, keys, policy settings, and metrics for a tenant."""
        with SessionLocal() as db:
            t = db.query(TenantDB).filter(TenantDB.id == tenant_id).first()
            if not t:
                return None

            api_keys_list = [
                ApiKeyModel(
                    id=k.id,
                    name=k.name,
                    publishable_key=k.publishable_key,
                    secret_key=k.secret_key,
                    environment=k.environment,
                    created_at_epoch=k.created_at_epoch,
                    status=k.status
                )
                for k in t.api_keys
            ]

            active_keys_count = sum(1 for k in api_keys_list if k.status == "active")

            settings_obj = TenantPolicySettings(
                allow_threshold=t.settings.allow_threshold if t.settings else 70,
                mfa_threshold=t.settings.mfa_threshold if t.settings else 40,
                block_threshold=t.settings.block_threshold if t.settings else 39,
                impossible_travel_enabled=t.settings.impossible_travel_enabled if t.settings else True,
                bot_cadence_enabled=t.settings.bot_cadence_enabled if t.settings else True,
                touch_biometrics_enabled=t.settings.touch_biometrics_enabled if t.settings else True,
                velocity_spike_enabled=t.settings.velocity_spike_enabled if t.settings else True,
                webhook_url=t.settings.webhook_url if t.settings else None,
                webhook_secret=t.settings.webhook_secret if t.settings else None
            )

            total_evals = t.metrics.total_evaluations if t.metrics else 0
            avg_lat = 0.0
            if total_evals > 0 and t.metrics:
                avg_lat = round(t.metrics.total_latency_ms / total_evals, 2)

            metrics_obj = TenantMetrics(
                total_evaluations=total_evals,
                allow_count=t.metrics.allow_count if t.metrics else 0,
                challenge_count=t.metrics.challenge_count if t.metrics else 0,
                block_count=t.metrics.block_count if t.metrics else 0,
                avg_latency_ms=avg_lat,
                active_keys_count=active_keys_count
            )

            return TenantProfile(
                id=t.id,
                name=t.name,
                email=t.email,
                industry=t.industry,
                plan=t.plan,
                created_at_epoch=t.created_at_epoch,
                api_keys=api_keys_list,
                settings=settings_obj,
                metrics=metrics_obj
            )

    def create_api_key(self, tenant_id: str, req: CreateApiKeyRequest) -> ApiKeyModel:
        """Generates a new API key pair for a tenant and persists to database."""
        prefix = "live" if req.environment == "live" else "test"
        key_id = f"key_{secrets.token_hex(6)}"
        pub_key = f"td_pub_{prefix}_{secrets.token_hex(8)}"
        sec_key = f"td_sec_{prefix}_{secrets.token_hex(16)}"
        now = time.time()

        with self._lock:
            with SessionLocal() as db:
                t = db.query(TenantDB).filter(TenantDB.id == tenant_id).first()
                if not t:
                    raise ValueError(f"Tenant '{tenant_id}' not found.")

                new_key_db = ApiKeyDB(
                    id=key_id,
                    tenant_id=tenant_id,
                    name=req.name,
                    publishable_key=pub_key,
                    secret_key=sec_key,
                    environment=req.environment,
                    created_at_epoch=now,
                    status="active"
                )

                db.add(new_key_db)
                db.commit()

                # Sync to fast in-memory cache
                self.key_index[pub_key] = (tenant_id, key_id)
                self.key_index[sec_key] = (tenant_id, key_id)

            return ApiKeyModel(
                id=key_id,
                name=req.name,
                publishable_key=pub_key,
                secret_key=sec_key,
                environment=req.environment,
                created_at_epoch=now,
                status="active"
            )

    def revoke_api_key(self, tenant_id: str, key_id: str) -> bool:
        """Revokes an API key pair and evicts from in-memory cache."""
        with self._lock:
            with SessionLocal() as db:
                key = db.query(ApiKeyDB).filter(ApiKeyDB.tenant_id == tenant_id, ApiKeyDB.id == key_id).first()
                if not key or key.status == "revoked":
                    return False

                key.status = "revoked"
                db.commit()

                # Evict from fast in-memory cache
                self.key_index.pop(key.publishable_key, None)
                self.key_index.pop(key.secret_key, None)
                return True

    def update_settings(self, tenant_id: str, new_settings: TenantPolicySettings) -> TenantPolicySettings:
        """Updates custom policy risk score thresholds and webhooks for a tenant."""
        with self._lock:
            with SessionLocal() as db:
                settings_db = db.query(TenantSettingsDB).filter(TenantSettingsDB.tenant_id == tenant_id).first()
                if not settings_db:
                    raise ValueError("Tenant settings not found.")

                settings_db.allow_threshold = new_settings.allow_threshold
                settings_db.mfa_threshold = new_settings.mfa_threshold
                settings_db.block_threshold = new_settings.block_threshold
                settings_db.impossible_travel_enabled = new_settings.impossible_travel_enabled
                settings_db.bot_cadence_enabled = new_settings.bot_cadence_enabled
                settings_db.touch_biometrics_enabled = new_settings.touch_biometrics_enabled
                settings_db.velocity_spike_enabled = new_settings.velocity_spike_enabled
                if new_settings.webhook_url is not None:
                    settings_db.webhook_url = new_settings.webhook_url
                if new_settings.webhook_secret is not None:
                    settings_db.webhook_secret = new_settings.webhook_secret

                db.commit()

                # Sync to fast in-memory cache
                self.settings_cache[tenant_id] = new_settings
                return new_settings

    def identify_tenant_by_key(self, key_str: Optional[str]) -> Optional[Tuple[str, TenantPolicySettings]]:
        """
        Ultra-fast O(1) in-memory lookup identifying tenant from a publishable or secret key.
        Executes on the critical scoring path in < 0.01ms.
        """
        if not key_str:
            return None
        
        clean_key = key_str.replace("Bearer ", "").strip()
        with self._lock:
            match = self.key_index.get(clean_key)
            if not match:
                return None
            tenant_id, _ = match
            settings = self.settings_cache.get(tenant_id)
            if not settings:
                settings = TenantPolicySettings()
            return tenant_id, settings

    def record_decision(self, tenant_id: str, decision_data: Dict[str, Any]):
        """Records an evaluation decision into persistent metrics and audit log table."""
        dec = str(decision_data.get("decision", "")).upper()
        lat = float(decision_data.get("latency_ms", 0.0))
        reasons_list = decision_data.get("reasons", [])
        reasons_str = json.dumps(reasons_list) if isinstance(reasons_list, list) else "[]"
        now = time.time()

        with SessionLocal() as db:
            # Update metrics
            metrics_db = db.query(TenantMetricsDB).filter(TenantMetricsDB.tenant_id == tenant_id).first()
            if metrics_db:
                metrics_db.total_evaluations += 1
                metrics_db.total_latency_ms += lat
                if dec == "ALLOW":
                    metrics_db.allow_count += 1
                elif dec == "CHALLENGE":
                    metrics_db.challenge_count += 1
                elif dec == "BLOCK":
                    metrics_db.block_count += 1

            # Insert audit log
            log_db = DecisionAuditLogDB(
                tenant_id=tenant_id,
                customer_id=decision_data.get("customer_id", "anon"),
                trust_score=float(decision_data.get("trust_score", 0)),
                decision=decision_data.get("decision", "ALLOW"),
                latency_ms=lat,
                reasons_json=reasons_str,
                amount=float(decision_data.get("amount", 0.0)),
                currency=str(decision_data.get("currency", "USD")),
                timestamp=now
            )
            db.add(log_db)
            db.commit()

    def get_tenant_audit_logs(self, tenant_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches isolated audit logs for a tenant from database ordered by most recent."""
        with SessionLocal() as db:
            logs = db.query(DecisionAuditLogDB)\
                     .filter(DecisionAuditLogDB.tenant_id == tenant_id)\
                     .order_by(DecisionAuditLogDB.timestamp.desc())\
                     .limit(limit)\
                     .all()

            return [
                {
                    "id": f"eval_{l.id}",
                    "timestamp": l.timestamp,
                    "customer_id": l.customer_id,
                    "trust_score": l.trust_score,
                    "decision": l.decision,
                    "latency_ms": l.latency_ms,
                    "reasons": json.loads(l.reasons_json or "[]"),
                    "amount": l.amount,
                    "currency": l.currency
                }
                for l in logs
            ]


# Global Singleton Tenant Engine
tenant_engine = MultiTenantEngine()
