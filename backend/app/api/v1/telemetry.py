"""Web telemetry collector tokenization and ML dataset export endpoints."""
import time
from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel, Field
from ...engine.tokens import create_telemetry_token
from ...engine.training import training_pipeline

router = APIRouter(tags=["Telemetry & ML Data"])


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
