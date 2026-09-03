"""Multi-Tenant Store and Account Management Engine for TrustDNA.
Handles client organization registration, authentication, API key lifecycle,
isolated metrics tracking, and per-tenant policy configurations.
"""
import hashlib
import hmac
import secrets
import time
import threading
from typing import Dict, List, Optional, Tuple, Any
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
        self.tenants: Dict[str, Dict[str, Any]] = {}
        self.email_to_id: Dict[str, str] = {}
        self.key_index: Dict[str, Tuple[str, str]] = {}  # key_str -> (tenant_id, key_id)
        self.audit_logs: Dict[str, List[Dict[str, Any]]] = {}  # tenant_id -> list of recent logs

    def register_tenant(self, req: TenantRegisterRequest) -> Tuple[TenantProfile, str]:

        """Registers a new organization and returns initial profile with generated default keys."""
        email_clean = req.email.strip().lower()
        with self._lock:
            if email_clean in self.email_to_id:
                raise ValueError("An organization with this email address already exists.")

            tenant_id = f"org_{secrets.token_hex(6)}"
            now = time.time()

            # Generate initial default key pair
            key_id = f"key_{secrets.token_hex(6)}"
            pub_key = f"td_pub_test_{secrets.token_hex(8)}"
            sec_key = f"td_sec_test_{secrets.token_hex(16)}"

            default_key = ApiKeyModel(
                id=key_id,
                name="Primary Sandbox Key",
                publishable_key=pub_key,
                secret_key=sec_key,
                environment="sandbox",
                created_at_epoch=now,
                status="active"
            )

            profile_dict = {
                "id": tenant_id,
                "name": req.name.strip(),
                "email": email_clean,
                "password_hash": _hash_password(req.password),
                "industry": req.industry.strip(),
                "plan": "Scale",
                "created_at_epoch": now,
                "api_keys": [default_key],
                "settings": TenantPolicySettings(),
                "metrics": TenantMetrics(active_keys_count=1)
            }

            self.tenants[tenant_id] = profile_dict
            self.email_to_id[email_clean] = tenant_id
            self.key_index[pub_key] = (tenant_id, key_id)
            self.key_index[sec_key] = (tenant_id, key_id)
            self.audit_logs[tenant_id] = []

            # Session token for auto-login
            session_token = f"td_sess_{tenant_id}_{secrets.token_hex(16)}"
            return self.get_profile(tenant_id), session_token

    def authenticate(self, req: TenantLoginRequest) -> Tuple[TenantProfile, str]:
        """Authenticates a tenant with email/password and returns profile + session token."""
        email_clean = req.email.strip().lower()
        with self._lock:
            tenant_id = self.email_to_id.get(email_clean)
            if not tenant_id:
                raise ValueError("Invalid email or password.")

            tenant_data = self.tenants.get(tenant_id)
            if not tenant_data or tenant_data["password_hash"] != _hash_password(req.password):
                raise ValueError("Invalid email or password.")

            session_token = f"td_sess_{tenant_id}_{secrets.token_hex(16)}"
            return self.get_profile(tenant_id), session_token

    def list_all_tenants(self) -> List[TenantSummary]:
        """Returns summary list of all registered and pre-seeded client organizations."""
        with self._lock:
            summaries = []
            for t in self.tenants.values():
                active_keys = sum(1 for k in t["api_keys"] if k.status == "active")
                summaries.append(TenantSummary(
                    id=t["id"],
                    name=t["name"],
                    email=t["email"],
                    industry=t["industry"],
                    active_keys_count=active_keys,
                    total_evaluations=t["metrics"].total_evaluations
                ))
            return summaries

    def get_profile(self, tenant_id: str) -> Optional[TenantProfile]:
        """Fetches complete profile for a tenant."""
        with self._lock:
            t = self.tenants.get(tenant_id)
            if not t:
                return None
            
            active_keys = sum(1 for k in t["api_keys"] if k.status == "active")
            metrics = t["metrics"]
            metrics.active_keys_count = active_keys

            return TenantProfile(
                id=t["id"],
                name=t["name"],
                email=t["email"],
                industry=t["industry"],
                plan=t["plan"],
                created_at_epoch=t["created_at_epoch"],
                api_keys=t["api_keys"],
                settings=t["settings"],
                metrics=metrics
            )

    def create_api_key(self, tenant_id: str, req: CreateApiKeyRequest) -> ApiKeyModel:
        """Generates a new API key pair (publishable & secret) for a tenant."""
        with self._lock:
            t = self.tenants.get(tenant_id)
            if not t:
                raise ValueError(f"Tenant '{tenant_id}' not found.")

            prefix = "live" if req.environment == "live" else "test"
            key_id = f"key_{secrets.token_hex(6)}"
            pub_key = f"td_pub_{prefix}_{secrets.token_hex(8)}"
            sec_key = f"td_sec_{prefix}_{secrets.token_hex(16)}"
            now = time.time()

            new_key = ApiKeyModel(
                id=key_id,
                name=req.name,
                publishable_key=pub_key,
                secret_key=sec_key,
                environment=req.environment,
                created_at_epoch=now,
                status="active"
            )

            t["api_keys"].append(new_key)
            self.key_index[pub_key] = (tenant_id, key_id)
            self.key_index[sec_key] = (tenant_id, key_id)
            return new_key

    def revoke_api_key(self, tenant_id: str, key_id: str) -> bool:
        """Revokes an API key pair so it can no longer be used for evaluation."""
        with self._lock:
            t = self.tenants.get(tenant_id)
            if not t:
                return False

            found = False
            for k in t["api_keys"]:
                if k.id == key_id:
                    k.status = "revoked"
                    found = True
                    # Remove from active lookup index
                    self.key_index.pop(k.publishable_key, None)
                    self.key_index.pop(k.secret_key, None)
                    break
            return found

    def update_settings(self, tenant_id: str, new_settings: TenantPolicySettings) -> TenantPolicySettings:
        """Updates custom policy risk score thresholds for a tenant."""
        with self._lock:
            t = self.tenants.get(tenant_id)
            if not t:
                raise ValueError("Tenant not found.")
            t["settings"] = new_settings
            return t["settings"]

    def identify_tenant_by_key(self, key_str: Optional[str]) -> Optional[Tuple[str, TenantPolicySettings]]:
        """
        Ultra-fast O(1) in-memory lookup identifying tenant from a publishable or secret key.
        Used on the critical evaluation path (< 0.01ms).
        """
        if not key_str:
            return None
        
        # Clean potential Bearer token prefix
        clean_key = key_str.replace("Bearer ", "").strip()
        with self._lock:
            match = self.key_index.get(clean_key)
            if not match:
                return None
            tenant_id, key_id = match
            t = self.tenants.get(tenant_id)
            if not t:
                return None
            return tenant_id, t["settings"]

    def record_decision(self, tenant_id: str, decision_data: Dict[str, Any]):
        """Records an evaluation decision into the tenant's isolated metrics and audit log."""
        with self._lock:
            t = self.tenants.get(tenant_id)
            if not t:
                return

            m = t["metrics"]
            m.total_evaluations += 1
            dec = str(decision_data.get("decision", "")).upper()
            if dec == "ALLOW":
                m.allow_count += 1
            elif dec == "CHALLENGE":
                m.challenge_count += 1
            elif dec == "BLOCK":
                m.block_count += 1


            # Update running average latency
            lat = decision_data.get("latency_ms", 0.0)
            if m.total_evaluations == 1:
                m.avg_latency_ms = round(lat, 2)
            else:
                m.avg_latency_ms = round((m.avg_latency_ms * 0.9) + (lat * 0.1), 2)

            # Prepend to tenant-isolated audit log (keep max 100 recent)
            logs = self.audit_logs.setdefault(tenant_id, [])
            log_record = {
                "id": f"eval_{secrets.token_hex(6)}",
                "timestamp": round(time.time(), 3),
                "customer_id": decision_data.get("customer_id", "anon"),
                "trust_score": decision_data.get("trust_score", 0),
                "decision": decision_data.get("decision", "ALLOW"),
                "latency_ms": lat,
                "reasons": decision_data.get("reasons", []),
                "amount": decision_data.get("amount", 0.0),
                "currency": decision_data.get("currency", "USD")
            }
            logs.insert(0, log_record)
            if len(logs) > 100:
                logs.pop()

    def get_tenant_audit_logs(self, tenant_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches isolated audit logs for a tenant."""
        with self._lock:
            return self.audit_logs.get(tenant_id, [])[:limit]


# Global Singleton Tenant Engine
tenant_engine = MultiTenantEngine()
