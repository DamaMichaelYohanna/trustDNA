"""TrustDNA SDK Data Models."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Subscores(BaseModel):
    device_health: float
    network_reputation: float
    travel_velocity: float
    behavioral_biometrics: float
    financial_velocity: float


class RiskDecision(BaseModel):
    customer_id: str
    trust_score: float
    decision: str  # "allow", "challenge", "block"
    reasons: List[str]
    subscores: Subscores
    latency_ms: float
    w3c_trace_id: Optional[str] = None
