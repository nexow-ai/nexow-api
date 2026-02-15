"""FastAPI application for nexow-api - Main API gateway."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
import structlog
import httpx

logger = structlog.get_logger(__name__)


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    port: int = 8000
    environment: str = "development"

    # Internal service URLs (override via env vars in production)
    nexow_agents_url: str = "http://localhost:8002"
    nexow_data_url: str = "http://localhost:8001"
    nexow_backtesting_url: str = "http://localhost:8003"

    # CORS
    cors_origins: list[str] = ["*"]


settings = Settings()

app = FastAPI(
    title="Nexow API Gateway",
    description="Main API gateway for Nexow trading platform",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "nexow-api"}


@app.get("/status")
async def get_status():
    """Get API gateway status."""
    return {
        "service": "nexow-api",
        "version": "0.1.0",
        "environment": settings.environment,
        "services": {
            "agents": settings.nexow_agents_url,
            "data": settings.nexow_data_url,
            "backtesting": settings.nexow_backtesting_url,
        }
    }


# ============================================================================
# Proxy endpoints to other services
# ============================================================================

@app.get("/api/prices/{instrument}")
async def get_price(instrument: str):
    """Proxy to nexow-data for price."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{settings.nexow_data_url}/prices/{instrument}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=str(e))


# TODO: Add more proxy endpoints:
# - /api/agents/* -> nexow-agents
# - /api/backtest -> nexow-backtesting
# - WebSocket support for real-time updates
