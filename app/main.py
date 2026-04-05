from fastapi import FastAPI

from app.api.adapter_instances import router as adapter_instances_router
from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.routes import router as routes_router
from app.api.rules import router as rules_router
from app.api.webhooks import router as webhooks_router
from app.config import get_settings
from app.dependencies import lifespan

settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(webhooks_router)
app.include_router(rules_router)
app.include_router(routes_router)
app.include_router(adapter_instances_router)
