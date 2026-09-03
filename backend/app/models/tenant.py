"""Pydantic data models for multi-tenant organizations, API keys, and auth."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class ApiKeyModel(BaseModel):
    id: str
    name: str
    publishable_key: str
    secret_key: str
    environment: str = "sandbox"  # 'sandbox' | 'live'
    created_at_epoch: float
    status: str = "active"  # 'active' | 'revoked'
    last_used_epoch: Optional[float] = None


class TenantPolicySettings(BaseModel):
    allow_threshold: int = Field(default=70, ge=0, le=100, description="Trust scores >= this value are allowed")
    mfa_threshold: int = Field(default=40, ge=0, le=100, description="Trust scores between mfa and allow trigger challenge")
    block_threshold: int = Field(default=39, ge=0, le=100, description="Trust scores <= this value are blocked")
    impossible_travel_enabled: bool = True
    bot_cadence_enabled: bool = True
    touch_biometrics_enabled: bool = True
    velocity_spike_enabled: bool = True
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None



class TenantMetrics(BaseModel):
    total_evaluations: int = 0
    allow_count: int = 0
    challenge_count: int = 0
    block_count: int = 0
    avg_latency_ms: float = 0.0
    active_keys_count: int = 0


class TenantRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Organization or Company Name")
    email: str = Field(..., description="Developer / Admin Email")
    password: str = Field(..., min_length=6, description="Account Password")
    industry: str = Field(default="Fintech / E-Commerce", description="Industry Sector")


class TenantLoginRequest(BaseModel):
    email: str
    password: str


class CreateApiKeyRequest(BaseModel):
    name: str = Field(default="Default Key Pair", max_length=50)
    environment: str = Field(default="sandbox", pattern="^(sandbox|live)$")


class TenantProfile(BaseModel):
    id: str
    name: str
    email: str
    industry: str
    plan: str = "Enterprise"
    created_at_epoch: float
    api_keys: List[ApiKeyModel] = []
    settings: TenantPolicySettings = Field(default_factory=TenantPolicySettings)
    metrics: TenantMetrics = Field(default_factory=TenantMetrics)


class TenantSummary(BaseModel):
    id: str
    name: str
    email: str
    industry: str
    active_keys_count: int
    total_evaluations: int
