from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.adapter_instances import router as adapter_instances_router
from app.api.vk_auth import router as vk_auth_router
from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.help import router as help_router
from app.api.routes import router as routes_router
from app.api.webhooks import router as webhooks_router
from app.config import get_settings
from app.dependencies import lifespan
from app.utils.logging import setup_logging

settings = get_settings()
setup_logging(settings)
app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

WEBUI_DIR = Path(__file__).resolve().parent / "webui"
app.mount("/static", StaticFiles(directory=WEBUI_DIR), name="webui-static")

app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(webhooks_router)
app.include_router(routes_router)
app.include_router(adapter_instances_router)
app.include_router(vk_auth_router)

app.include_router(help_router)
