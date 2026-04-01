from sqlalchemy import delete, select

from app.db.models import RouteORM
from app.domain.enums import Platform
from app.domain.policies import Route
from app.repositories.base import SQLAlchemyRepo
from app.repositories.sql.converters import orm_to_route


class RoutesRepo(SQLAlchemyRepo):
    async def upsert(self, route: Route) -> Route:
        row = await self.session.get(RouteORM, route.id)
        if row is None:
            row = RouteORM(
                id=route.id,
                source_platform=route.source_platform.value,
                source_chat_id=route.source_chat_id,
                target_platform=route.target_platform.value,
                target_chat_id=route.target_chat_id,
                enabled=route.enabled,
            )
            self.session.add(row)
        else:
            row.source_platform = route.source_platform.value
            row.source_chat_id = route.source_chat_id
            row.target_platform = route.target_platform.value
            row.target_chat_id = route.target_chat_id
            row.enabled = route.enabled

        await self.session.commit()
        await self.session.refresh(row)
        return orm_to_route(row)

    async def get(self, route_id: str) -> Route | None:
        row = await self.session.get(RouteORM, route_id)
        return orm_to_route(row) if row else None

    async def list_all(self) -> list[Route]:
        rows = (await self.session.execute(select(RouteORM).order_by(RouteORM.id))).scalars().all()
        return [orm_to_route(row) for row in rows]

    async def delete(self, route_id: str) -> bool:
        result = await self.session.execute(delete(RouteORM).where(RouteORM.id == route_id))
        await self.session.commit()
        return (result.rowcount or 0) > 0

    async def list_enabled_for_source(self, source_platform: Platform, source_chat_id: str) -> list[Route]:
        rows = (
            await self.session.execute(
                select(RouteORM)
                .where(
                    RouteORM.enabled.is_(True),
                    RouteORM.source_platform == source_platform.value,
                    RouteORM.source_chat_id == source_chat_id,
                )
                .order_by(RouteORM.id)
            )
        ).scalars().all()
        return [orm_to_route(row) for row in rows]
