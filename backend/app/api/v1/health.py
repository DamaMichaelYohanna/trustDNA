"""System health, readiness, and observability endpoints."""
import time
from fastapi import APIRouter
from pydantic import BaseModel
from ...engine.audit import audit_logger
from ...engine.tenants import tenant_engine
from ...config import settings

router = APIRouter(tags=["Health & Diagnostics"])

SERVER_START_TIME = time.time()


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    engine: str
    velocity_store: str
    total_audited_decisions: int
    active_tenants: int


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint confirming engine readiness, uptime, and store architecture."""
    store_type = "Distributed Redis" if settings.redis_url else "Bounded In-Memory (Zero-Leak)"
    return HealthResponse(
        status="healthy",
        version=settings.version,
        uptime_seconds=round(time.time() - SERVER_START_TIME, 2),
        engine="TrustDNA Heuristic Rule Engine (Stage 2 Multi-Tenant)",
        velocity_store=store_type,
        total_audited_decisions=audit_logger.total_logged,
        active_tenants=len(tenant_engine.list_all_tenants())
    )



@router.get("/audit/recent")
async def get_recent_audit_trail(limit: int = 20):
    """Administrative endpoint to inspect global non-blocking audit trail."""
    return {
        "count": audit_logger.total_logged,
        "records": audit_logger.get_recent_logs(limit=limit)
    }
