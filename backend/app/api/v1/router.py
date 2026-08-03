"""
Main API v1 router aggregating 
all v1 sub-routers.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(health_router)
