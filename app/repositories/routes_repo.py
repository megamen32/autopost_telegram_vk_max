from sqlalchemy import delete, select

from app.db.models import RouteORM
from app.domain.policies import Route
from app.repositories.base import SQLAlchemyRepo
from app.repositories.sql.converters import orm_to_route


class RoutesRepo(SQLAlchemyRepo):
    async def upsert(self, route: Route) -> Route:
        row = await self.session.get(RouteORM, route.id)
        if row is None:
            row = RouteORM(id=route.id)
            self.session.add(row)

        row.source_adapter_id = route.source_adapter_id
        row.source_platform = route.source_platform.value
        row.source_chat_id = route.source_chat_id
        row.target_adapter_id = route.target_adapter_id
        row.target_platform = route.target_platform.value
        row.target_chat_id = route.target_chat_id
        row.enabled = route.enabled
        row.has_policy = route.has_policy
        row.policy_enabled = route.policy_enabled
        row.allow_text = route.content_policy.allow_text
        row.allow_images = route.content_policy.allow_images
        row.allow_video = route.content_policy.allow_video
        row.allow_audio = route.content_policy.allow_audio
        row.allow_documents = route.content_policy.allow_documents
        row.allow_reposts = route.content_policy.allow_reposts
        row.max_images = route.content_policy.max_images
        row.max_video_size_mb = route.content_policy.max_video_size_mb
        row.max_audio_size_mb = route.content_policy.max_audio_size_mb
        row.drop_unsupported_media = route.content_policy.drop_unsupported_media
        row.repost_mode = route.repost_mode.value
        row.copy_text_template = route.copy_text_template

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

    async def list_enabled_for_source(self, source_adapter_id: str, source_chat_id: str) -> list[Route]:
        rows = (
            await self.session.execute(
                select(RouteORM)
                .where(
                    RouteORM.enabled.is_(True),
                    RouteORM.source_adapter_id == source_adapter_id,
                    RouteORM.source_chat_id == source_chat_id,
                )
                .order_by(RouteORM.id)
            )
        ).scalars().all()
        return [orm_to_route(row) for row in rows]
