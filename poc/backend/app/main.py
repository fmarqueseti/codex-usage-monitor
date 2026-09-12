from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from poc.backend.app.api.routes.health import router as health_router
from poc.backend.app.api.routes.usage import router as usage_router
from poc.backend.app.config import cache_ttl, configure_logging
from poc.backend.app.providers.factory import build_provider
from poc.backend.app.services.usage_service import UsageService

configure_logging()
app = FastAPI(title="Codex Usage Monitor", version="0.1.0")
app.state.usage_service = UsageService(build_provider(), cache_ttl())
app.include_router(health_router)
app.include_router(usage_router)
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[3] / "frontend", html=True), name="frontend")
