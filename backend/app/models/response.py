"""Pydantic schemas for risk evaluation responses."""
from typing import List, Literal
from pydantic import BaseModel, Field


class ReasonTag(BaseModel):
    text: str
    type: Literal["success", "warning", "danger"]


class ModuleScores(BaseModel):
    device: int = Field(..., ge=0, le=100, description="Device integrity & profile score")
    network: int = Field(..., ge=0, le=100, description="Network hygiene & proxy risk score")
    behavior: int = Field(..., ge=0, le=100, description="Passive behavioral biometrics score")
    transaction: int = Field(..., ge=0, le=100, description="Spending anomaly & velocity score")


class RiskEvaluationResponse(BaseModel):
    trust_score: int = Field(..., ge=0, le=100, description="Overall composite trust score")
    decision: Literal["allow", "challenge", "block"] = Field(..., description="Actionable decision")
    risk_level: Literal["low", "medium", "high"] = Field(..., description="Risk tier")
    latency_ms: float = Field(..., description="Server evaluation execution duration in milliseconds")
    customer_id: str = Field(..., description="User/Account reference")
    reasons: List[str] = Field(..., description="Machine-readable triggered security flags")
    reason_details: List[ReasonTag] = Field(default_factory=list, description="Categorized tags for UI display")
    module_scores: ModuleScores
    recommended_action: Literal["proceed", "require_totp_mfa", "block_and_terminate_session"]
