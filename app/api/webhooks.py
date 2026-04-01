from fastapi import APIRouter, Request

from app.dependencies import container
from app.domain.enums import Platform

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/{platform}")
async def webhook_handler(platform: Platform, request: Request):
    payload = await request.json()
    await container.ingress_service.handle_event(platform=platform, payload=payload)
    return {"ok": True}
