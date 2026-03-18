"""Dawai Yaad — API Router Aggregation."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.medications import router as medications_router
from app.api.health import router as health_router
from app.api.sos import router as sos_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(medications_router)
api_router.include_router(health_router)
api_router.include_router(sos_router)
