"""TradeAI FastAPI application entry point."""

from fastapi import FastAPI

from app.domain.schemas.health import HealthResponse

app = FastAPI(
    title="TradeAI",
    description="Enterprise-grade AI-native trading operating system",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint for load balancers and Docker."""
    return HealthResponse()
