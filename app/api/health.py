from fastapi import APIRouter

from app.dependencies import container

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {
        "ok": True,
        "platforms": container.adapter_registry.list_platforms(),
    }


@router.get("/debug/message-links")
async def debug_message_links():
    return await container.message_links_repo.list_all()


@router.get("/debug/processed-events")
async def debug_processed_events():
    return await container.processed_events_repo.list_all()
