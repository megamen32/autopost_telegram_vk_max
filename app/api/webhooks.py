from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_container, get_session

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/{adapter_instance_id}")
async def webhook_handler(
    adapter_instance_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    container=Depends(get_container),
):
    payload = await request.json()
    try:
        adapter = container.adapter_registry.get_by_instance(adapter_instance_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    preprocessed = await adapter.preprocess_webhook(payload, request=request)
    if preprocessed is not None:
        return preprocessed

    ingress_service = container.create_ingress_service(session)
    await ingress_service.handle_event(adapter_instance_id=adapter_instance_id, payload=payload)
    return {"ok": True}
