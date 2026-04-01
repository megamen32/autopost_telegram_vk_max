from fastapi import APIRouter, HTTPException

from app.dependencies import container
from app.domain.policies import ContentPolicy, SyncRule
from app.schemas.api import SyncRuleSchema

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("")
async def list_rules():
    return await container.rules_repo.list_all()


@router.post("")
async def create_or_update_rule(payload: SyncRuleSchema):
    rule = SyncRule(
        source_platform=payload.source_platform,
        target_platform=payload.target_platform,
        enabled=payload.enabled,
        content_policy=ContentPolicy(**payload.content_policy.model_dump()),
        repost_mode=payload.repost_mode,
        copy_text_template=payload.copy_text_template,
    )
    return await container.rules_repo.upsert(rule)


@router.delete("/{source_platform}/{target_platform}")
async def delete_rule(source_platform: str, target_platform: str):
    from app.domain.enums import Platform

    try:
        deleted = await container.rules_repo.delete(Platform(source_platform), Platform(target_platform))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"ok": True}
