"""
FastAPI application factory for OpenBench.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine
from app.models import (  # noqa: F401  — ensure all models are registered
    AuditLog, Badge, Booking, ConditionReport, CreditTransaction,
    Equipment, EquipmentAvailabilityWindow, Incident, Lab, LabMembership,
    Notification, ActionProposal, Strike, User, UserCredential, WaitlistEntry,
)
from app.database import Base
from app.routers import auth, labs, equipment, bookings, proposals, audit, credits, admin, notifications
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── startup ──────────────────────────────────────────────────────────────
    Base.metadata.create_all(bind=engine)

    if os.getenv("AUTO_SEED", "false").lower() == "true":
        _auto_seed()

    start_scheduler()

    yield

    # ── shutdown ─────────────────────────────────────────────────────────────
    stop_scheduler()


def _auto_seed() -> None:
    from app.database import SessionLocal
    from app.seed import run_seed
    from app.models import User as UserModel

    db = SessionLocal()
    try:
        if db.query(UserModel).count() == 0:
            run_seed(db, wipe=False)
    except Exception as exc:
        print(f"[AUTO_SEED] failed: {exc}")
    finally:
        db.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title="OpenBench API",
        version="0.1.0",
        description="Trusted platform to share underused lab equipment and spaces.",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    origins = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8000").split(",")
        if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API routes ────────────────────────────────────────────────────────────
    api_prefix = "/api"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(labs.router, prefix=api_prefix)
    app.include_router(equipment.router, prefix=api_prefix)
    app.include_router(bookings.router, prefix=api_prefix)
    app.include_router(proposals.router, prefix=api_prefix)
    app.include_router(audit.router, prefix=api_prefix)
    app.include_router(credits.router, prefix=api_prefix)
    app.include_router(admin.router, prefix=api_prefix)
    app.include_router(notifications.router, prefix=api_prefix)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/api/health", tags=["health"])
    def health():
        from app.clock import app_now
        return {"status": "ok", "app_now": app_now().isoformat()}

    # ── Serve React static build ──────────────────────────────────────────────
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()

