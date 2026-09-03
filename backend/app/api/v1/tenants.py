"""Tenant profile, API key lifecycle, audit log stream, and policy settings endpoints."""
from typing import List
from fastapi import APIRouter, HTTPException, status
from ...models.tenant import (
    ApiKeyModel,
    TenantPolicySettings,
    CreateApiKeyRequest,
    TenantProfile
)
from ...engine.tenants import tenant_engine

router = APIRouter(prefix="/tenant", tags=["Tenant Account Management"])


@router.get("/{tenant_id}/profile", response_model=TenantProfile)
async def get_tenant_profile(tenant_id: str):
    """Fetches full profile, keys, policy settings, and metrics for a tenant."""
    profile = tenant_engine.get_profile(tenant_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return profile


@router.get("/{tenant_id}/keys", response_model=List[ApiKeyModel])
async def get_tenant_api_keys(tenant_id: str):
    """Lists all active and revoked API keys for an organization."""
    profile = tenant_engine.get_profile(tenant_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return profile.api_keys


@router.post("/{tenant_id}/keys", response_model=ApiKeyModel)
async def create_tenant_api_key(tenant_id: str, payload: CreateApiKeyRequest):
    """Generates a new publishable and secret key pair for an organization."""
    try:
        new_key = tenant_engine.create_api_key(tenant_id, payload)
        return new_key
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{tenant_id}/keys/{key_id}/revoke")
async def revoke_tenant_api_key(tenant_id: str, key_id: str):
    """Revokes an API key pair immediately."""
    revoked = tenant_engine.revoke_api_key(tenant_id, key_id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found or already revoked")
    return {"status": "revoked", "key_id": key_id}


@router.put("/{tenant_id}/settings", response_model=TenantPolicySettings)
async def update_tenant_policy_settings(tenant_id: str, payload: TenantPolicySettings):
    """Updates custom risk score thresholds and feature toggles for an organization."""
    try:
        updated = tenant_engine.update_settings(tenant_id, payload)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{tenant_id}/audit-logs")
async def get_tenant_audit_logs(tenant_id: str, limit: int = 50):
    """Fetches real-time decision logs isolated for this organization."""
    logs = tenant_engine.get_tenant_audit_logs(tenant_id, limit=limit)
    return {"tenant_id": tenant_id, "count": len(logs), "logs": logs}
