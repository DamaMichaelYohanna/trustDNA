"""Aggregates all modular v1 API routers into a single master router."""
from fastapi import APIRouter
from .health import router as health_router
from .auth import router as auth_router
from .tenants import router as tenants_router
from .risk import router as risk_router
from .telemetry import router as telemetry_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(tenants_router)
api_v1_router.include_router(risk_router)
api_v1_router.include_router(telemetry_router)

__all__ = ["api_v1_router"]
