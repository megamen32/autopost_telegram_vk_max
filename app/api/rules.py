from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.domain.policies import ContentPolicy, SyncRule
from app.repositories.rules_repo import RulesRepo
from app.schemas.api import SyncRuleSchema

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("")
async def list_rules(session: AsyncSession = Depends(get_session)):
    return await RulesRepo(session).list_all()


@router.post("")
async def create_or_update_rule(payload: SyncRuleSchema, session: AsyncSession = Depends(get_session)):
    rule = SyncRule(
        source_platform=payload.source_platform,
        target_platform=payload.target_platform,
        enabled=payload.enabled,
        content_policy=ContentPolicy(**payload.content_policy.model_dump()),
        repost_mode=payload.repost_mode,
        copy_text_template=payload.copy_text_template,
    )
    return await RulesRepo(session).upsert(rule)


@router.delete("/{source_platform}/{target_platform}")
async def delete_rule(source_platform: str, target_platform: str, session: AsyncSession = Depends(get_session)):
    from app.domain.enums import Platform

    try:
        deleted = await RulesRepo(session).delete(Platform(source_platform), Platform(target_platform))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"ok": True}
