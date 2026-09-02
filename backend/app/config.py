"""Configuration and threshold definitions for TrustDNA Risk Engine."""
from pydantic import BaseModel


class RiskWeights(BaseModel):
    device: float = 0.30
    network: float = 0.25
    behavior: float = 0.25
    transaction: float = 0.20


class DecisionThresholds(BaseModel):
    allow_min: int = 75
    challenge_min: int = 40
    # Scores < 40 result in BLOCK


class Settings(BaseModel):
    app_name: str = "TrustDNA Risk Intelligence Engine"
    version: str = "1.0.0"
    debug: bool = False
    max_realistic_travel_speed_kmh: float = 800.0
    weights: RiskWeights = RiskWeights()
    thresholds: DecisionThresholds = DecisionThresholds()
    
    # High-Throughput & Database Bottleneck Prevention Settings
    redis_url: str | None = None  # e.g., "redis://localhost:6379/0" for distributed multi-worker setups
    max_in_memory_entities: int = 50000  # Hard memory ceiling to prevent unbounded RAM leaks
    enable_background_audit_logging: bool = True


settings = Settings()
