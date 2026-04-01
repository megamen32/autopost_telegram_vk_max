from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_container, get_session
from app.repositories.message_links_repo import MessageLinksRepo
from app.repositories.processed_events_repo import ProcessedEventsRepo

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(container=Depends(get_container)):
    return {
        "ok": True,
        "platforms": container.adapter_registry.list_platforms(),
    }


@router.get("/debug/message-links")
async def debug_message_links(session: AsyncSession = Depends(get_session)):
    return await MessageLinksRepo(session).list_all()


@router.get("/debug/processed-events")
async def debug_processed_events(session: AsyncSession = Depends(get_session)):
    return await ProcessedEventsRepo(session).list_all()
