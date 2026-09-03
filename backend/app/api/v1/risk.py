"""Real-time risk assessment, key attribution, and sandbox generator endpoints."""
import time
import secrets
from typing import Optional
from fastapi import APIRouter, Header, BackgroundTasks
from pydantic import BaseModel
from ...models.request import RiskEvaluationRequest
from ...models.response import RiskEvaluationResponse
from ...engine.scorer import evaluate_risk
from ...engine.audit import audit_logger
from ...engine.tenants import tenant_engine
from ...config import settings

router = APIRouter(tags=["Risk Evaluation"])


class KeyGenerateRequest(BaseModel):
    app_name: str = "My Test App"
    environment: str = "sandbox"


class KeyGenerateResponse(BaseModel):
    app_name: str
    environment: str
    publishable_key: str
    secret_key: str
    created_at_epoch: float


@router.post("/risk/evaluate", response_model=RiskEvaluationResponse)
def evaluate_transaction_risk(
    payload: RiskEvaluationRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_trustdna_key: Optional[str] = Header(None, alias="X-TrustDNA-Key"),
    x_publishable_key: Optional[str] = Header(None, alias="X-Publishable-Key")
):
    """
    Real-time risk assessment endpoint.
    Ingests opaque telemetry across device, network, travel, behavior, and transaction vectors.
    Returns composite score, actionable decision (ALLOW / CHALLENGE / BLOCK), and reason codes in < 1ms.
    
    Multi-Tenant Key Attribution:
    Automatically identifies calling tenant organization and logs metrics directly to their dashboard.
    """
    passed_key = x_trustdna_key or authorization or x_publishable_key
    tenant_match = tenant_engine.identify_tenant_by_key(passed_key)

    decision_result = evaluate_risk(payload)

    # Attribution to calling tenant
    if tenant_match:
        tenant_id, _ = tenant_match
        tenant_engine.record_decision(
            tenant_id,
            {
                "customer_id": decision_result.customer_id,
                "trust_score": decision_result.trust_score,
                "decision": decision_result.decision,
                "latency_ms": decision_result.latency_ms,
                "reasons": decision_result.reasons,
                "amount": payload.transaction.amount,
                "currency": payload.transaction.currency
            }
        )

    # Decouple persistent audit write from client response path
    if settings.enable_background_audit_logging:
        background_tasks.add_task(
            audit_logger.log_decision,
            {
                "customer_id": decision_result.customer_id,
                "trust_score": decision_result.trust_score,
                "decision": decision_result.decision,
                "latency_ms": decision_result.latency_ms,
                "reasons": decision_result.reasons,
                "amount": payload.transaction.amount,
                "currency": payload.transaction.currency
            }
        )

    return decision_result


@router.post("/keys/generate", response_model=KeyGenerateResponse)
async def generate_sandbox_keys(payload: KeyGenerateRequest):
    """Generates sandbox API keys for quick playground testing."""
    hex_token = secrets.token_hex(16)
    pub_key = f"td_pub_test_{hex_token[:16]}"
    sec_key = f"td_sec_test_{hex_token}"

    return KeyGenerateResponse(
        app_name=payload.app_name,
        environment=payload.environment,
        publishable_key=pub_key,
        secret_key=sec_key,
        created_at_epoch=time.time()
    )
