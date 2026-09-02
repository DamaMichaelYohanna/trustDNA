import uuid
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .config import settings
from .api.routes import router

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="The Programmable Trust Layer for Modern Digital Applications (Stripe for Risk Decisions).",
    docs_url="/docs",
    redoc_url="/redoc"
)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Adds X-Request-ID and W3C Server-Timing headers for zero-latency distributed tracing."""
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()
        
        response: Response = await call_next(request)
        
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Request-ID"] = req_id
        response.headers["Server-Timing"] = f"total;dur={duration_ms:.2f}"
        return response


app.add_middleware(ObservabilityMiddleware)

# Configure CORS so the Vite/vanilla frontend can seamlessly query the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits localhost:5173, Vercel deployments, and testing environments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to TrustDNA Risk Intelligence API",
        "docs": "/docs",
        "health": "/api/v1/health",
        "version": settings.version
    }
