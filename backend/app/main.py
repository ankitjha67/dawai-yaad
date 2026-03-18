"""
Dawai Yaad — Main FastAPI Application
=====================================
Open-source family health platform.
100% Free · Unlimited Medicines · Multi-Profile · Hospital Integration

GitHub: https://github.com/ankitjha67/dawai-yaad
License: MIT
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import engine, Base
from app.api import api_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — create tables on startup."""
    # Import all models so Base.metadata knows about them
    from app.models import (  # noqa: F401
        User, Family, FamilyMember,
        Medication, DoseLog,
        Measurement, MoodLog, SymptomLog,
        SOSAlert, Document, Notification,
        Hospital, HospitalStaff, PatientAssignment,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Dawai Yaad API",
    description=(
        "Open-source family health platform — medication reminders, "
        "health tracking, SOS alerts, hospital/nurse integration. "
        "Built for Indian families."
    ),
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────
app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "app": "Dawai Yaad",
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "description": "Open-source family health platform. 100% free, unlimited medicines.",
    }


@app.get("/health", tags=["Root"])
async def health_check():
    return {"status": "healthy"}
