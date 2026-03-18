"""Dawai Yaad — API Router Aggregation."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.medications import router as medications_router
from app.api.health import router as health_router
from app.api.sos import router as sos_router
from app.api.family import router as family_router
from app.api.users import router as users_router
from app.api.notifications import router as notifications_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(medications_router)
api_router.include_router(health_router)
api_router.include_router(sos_router)
api_router.include_router(family_router)
api_router.include_router(users_router)
api_router.include_router(notifications_router)
