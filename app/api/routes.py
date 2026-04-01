from fastapi import APIRouter, HTTPException

from app.dependencies import container
from app.domain.policies import Route
from app.schemas.api import RouteSchema

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("")
async def list_routes():
    return await container.routes_repo.list_all()


@router.post("")
async def create_or_update_route(payload: RouteSchema):
    route = Route(**payload.model_dump())
    return await container.routes_repo.upsert(route)


@router.delete("/{route_id}")
async def delete_route(route_id: str):
    deleted = await container.routes_repo.delete(route_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Route not found")
    return {"ok": True}
