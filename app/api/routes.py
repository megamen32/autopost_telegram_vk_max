from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.policies import ContentPolicy, Route
from app.repositories.routes_repo import RoutesRepo
from app.schemas.api import RouteSchema
from app.dependencies import get_session

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("")
async def list_routes(session: AsyncSession = Depends(get_session)):
    return await RoutesRepo(session).list_all()


@router.post("")
async def create_or_update_route(payload: RouteSchema, session: AsyncSession = Depends(get_session)):
    data = payload.model_dump()
    data["content_policy"] = ContentPolicy(**payload.content_policy.model_dump())
    route = Route(**data)
    return await RoutesRepo(session).upsert(route)


@router.delete("/{route_id}")
async def delete_route(route_id: str, session: AsyncSession = Depends(get_session)):
    deleted = await RoutesRepo(session).delete(route_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Route not found")
    return {"ok": True}
