"""TradeAI FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(
    title="TradeAI",
    description="Enterprise-grade AI-native trading operating system",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint for load balancers and Docker."""
    return {"status": "ok"}
