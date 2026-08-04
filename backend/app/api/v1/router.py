"""Main API v1 router aggregating all v1 sub-routers."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.market_data.router import router as market_data_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(health_router)
router.include_router(market_data_router)
