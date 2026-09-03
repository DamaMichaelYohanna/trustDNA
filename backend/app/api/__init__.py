"""API routes package."""
from .v1 import api_v1_router

# Router with standard /api/v1 prefix
router = api_v1_router

__all__ = ["router", "api_v1_router"]
