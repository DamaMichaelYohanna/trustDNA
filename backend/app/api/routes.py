"""REST API endpoints for TrustDNA risk evaluation and key management."""
import time
import secrets
from typing import Optional, Dict, Any
from fastapi import APIRouter, Header, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from ..models.request import RiskEvaluationRequest
from ..models.response import RiskEvaluationResponse
from ..engine.scorer import evaluate_risk
from ..engine.audit import audit_logger
from ..engine.velocity import velocity_tracker
from ..engine.tokens import create_telemetry_token
from ..engine.training import training_pipeline
from ..config import settings

router = APIRouter(prefix="/api/v1", tags=["TrustDNA Risk Engine"])

SERVER_START_TIME = time.time()


class KeyGenerateRequest(BaseModel):
    app_name: str = "My Test App"
    environment: str = "sandbox"


class KeyGenerateResponse(BaseModel):
    app_name: str
    environment: str
    publishable_key: str
    secret_key: str
    created_at_epoch: float


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    engine: str
    velocity_store: str
    total_audited_decisions: int


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint confirming engine readiness, uptime, and store architecture."""
    store_type = "Distributed Redis" if settings.redis_url else "Bounded In-Memory (Zero-Leak)"
    return HealthResponse(
        status="healthy",
        version=settings.version,
        uptime_seconds=round(time.time() - SERVER_START_TIME, 2),
        engine="TrustDNA Heuristic Rule Engine (Stage 1)",
        velocity_store=store_type,
        total_audited_decisions=audit_logger.total_logged
    )


@router.post("/risk/evaluate", response_model=RiskEvaluationResponse)
def evaluate_transaction_risk(
    payload: RiskEvaluationRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_trustdna_key: Optional[str] = Header(None, alias="X-TrustDNA-Key")
):
    """
    Real-time risk assessment endpoint.
    Ingests opaque telemetry across device, network, travel, behavior, and transaction vectors.
    Returns composite score, actionable decision (ALLOW / CHALLENGE / BLOCK), and reason codes in < 1ms.
    
    Database / Audit Logging: Executed strictly asynchronously out-of-band via BackgroundTasks
    guaranteeing ZERO database bottlenecks on the critical evaluation loop.
    """
    decision_result = evaluate_risk(payload)

    # Decouple database / persistent write from the client response path
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


@router.get("/audit/recent")
async def get_recent_audit_trail(limit: int = 20):
    """Administrative endpoint to inspect non-blocking audit trail."""
    return {
        "count": audit_logger.total_logged,
        "records": audit_logger.get_recent_logs(limit=limit)
    }


@router.post("/keys/generate", response_model=KeyGenerateResponse)
async def generate_sandbox_keys(payload: KeyGenerateRequest):
    """Generates sandbox API keys for developer testing."""
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


class TokenizeRequest(BaseModel):
    publishable_key: str = Field(..., description="Client publishable key (td_pub_...)")
    signals: Dict[str, Any] = Field(..., description="Opaque telemetry features (entropy, flight times, dwell times)")


class TokenizeResponse(BaseModel):
    telemetry_token: str
    issued_at_epoch: float
    expires_in_seconds: int = 3600


@router.post("/telemetry/tokenize", response_model=TokenizeResponse)
async def create_client_telemetry_token(payload: TokenizeRequest):
    """
    Exchanges client-side telemetry signals into an opaque signed token (td_tok_...).
    Called by trustdna.js on customer frontends using Publishable Keys.
    """
    token = create_telemetry_token(payload.signals, publishable_key=payload.publishable_key)
    return TokenizeResponse(
        telemetry_token=token,
        issued_at_epoch=time.time(),
        expires_in_seconds=3600
    )


@router.get("/ml/dataset")
async def export_training_dataset(limit: int = 100):
    """
    Exports anonymous mathematical feature vectors for training classical ML models (XGBoost / Isolation Forest).
    Zero PII footprint.
    """
    return {
        "total_records_collected": training_pipeline.total_records,
        "sample_count": min(limit, training_pipeline.total_records),
        "records": training_pipeline.get_dataset(limit=limit)
    }
