from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.charge import router as charge_router
from app.api.chat import router as chat_router
from app.api.chat import v1_router as v1_chat_router
from app.api.datasets import router as datasets_router
from app.api.meta import router as meta_router
from app.core.config import Settings, get_settings
from app.core.security import generate_access_token
from app.db.session import build_engine, build_session_factory, init_db
from app.schemas.common import HealthResponse
from app.services.auth_service import bootstrap_admin
from app.services.battery_service import seed_example_batteries
from app.services.invite_service import seed_public_demo_invite


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    engine = build_engine(resolved_settings.database_url)
    session_factory = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(engine)
        with session_factory() as db:
            bootstrap_admin(db, resolved_settings)
            seed_public_demo_invite(db, resolved_settings)
            seed_example_batteries(db)
        yield

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.admin_tokens = set()
    app.state.admin_username = resolved_settings.admin_username
    app.state.engine = engine
    app.state.SessionLocal = session_factory

    def issue_admin_token(_: str) -> str:
        token = generate_access_token(prefix="admin")
        app.state.admin_tokens.add(token)
        return token

    app.state.issue_admin_token = issue_admin_token

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service=resolved_settings.app_name)

    @app.get("/api/health", response_model=HealthResponse)
    def api_health() -> HealthResponse:
        return HealthResponse(status="ok", service=resolved_settings.app_name)

    app.include_router(auth_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.include_router(charge_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(v1_chat_router, prefix="/api")
    app.include_router(datasets_router, prefix="/api")
    app.include_router(meta_router, prefix="/api")

    return app


app = create_app()
