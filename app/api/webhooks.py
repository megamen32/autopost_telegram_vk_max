from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_container, get_session
from app.domain.enums import Platform

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/{platform}")
async def webhook_handler(
    platform: Platform,
    request: Request,
    session: AsyncSession = Depends(get_session),
    container=Depends(get_container),
):
    payload = await request.json()
    ingress_service = container.create_ingress_service(session)
    await ingress_service.handle_event(platform=platform, payload=payload)
    return {"ok": True}
