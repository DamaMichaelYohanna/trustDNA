"""Multi-tenant authentication, registration, and session endpoints."""
from typing import List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from ...models.tenant import (
    TenantRegisterRequest,
    TenantLoginRequest,
    TenantProfile,
    TenantSummary
)
from ...engine.tenants import tenant_engine

router = APIRouter(prefix="/auth", tags=["Multi-Tenant Auth"])


class AuthResponse(BaseModel):
    session_token: str
    tenant: TenantProfile


@router.post("/register", response_model=AuthResponse)
async def register_organization(payload: TenantRegisterRequest):
    """Registers a new client organization with initial sandbox API keys."""
    try:
        profile, session_token = tenant_engine.register_tenant(payload)
        return AuthResponse(session_token=session_token, tenant=profile)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=AuthResponse)
async def login_organization(payload: TenantLoginRequest):
    """Authenticates a client organization and returns profile + session token."""
    try:
        profile, session_token = tenant_engine.authenticate(payload)
        return AuthResponse(session_token=session_token, tenant=profile)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/tenants", response_model=List[TenantSummary])
async def list_available_tenants():
    """Lists registered client organizations."""
    return tenant_engine.list_all_tenants()
