from sqlalchemy import delete, select

from app.db.models import RouteORM
from app.domain.policies import ContentPolicy, Route
from app.repositories.base import SQLAlchemyRepo
from app.repositories.sql.converters import orm_to_route
from app.utils.chat_refs import canonicalize_telegram_chat_ref


def _normalize_content_policy(value) -> ContentPolicy:
    if isinstance(value, ContentPolicy):
        return value

    if isinstance(value, dict):
        return ContentPolicy(
            allow_text=value.get("allow_text", True),
            allow_images=value.get("allow_images", True),
            allow_video=value.get("allow_video", True),
            allow_audio=value.get("allow_audio", True),
            allow_documents=value.get("allow_documents", False),
            allow_reposts=value.get("allow_reposts", False),
            max_images=value.get("max_images"),
            max_video_size_mb=value.get("max_video_size_mb"),
            max_audio_size_mb=value.get("max_audio_size_mb"),
            drop_unsupported_media=value.get("drop_unsupported_media", True),
        )

    return ContentPolicy()


class RoutesRepo(SQLAlchemyRepo):
    async def upsert(self, route: Route) -> Route:
        row = await self.session.get(RouteORM, route.id)
        if row is None:
            row = RouteORM(id=route.id)
            self.session.add(row)

        row.source_adapter_id = route.source_adapter_id
        row.source_platform = route.source_platform.value
        row.source_chat_id = route.source_chat_id
        row.source_chat_canonical = route.source_chat_canonical
        row.target_adapter_id = route.target_adapter_id
        row.target_platform = route.target_platform.value
        row.target_chat_id = route.target_chat_id
        row.target_chat_canonical = route.target_chat_canonical
        row.enabled = route.enabled
        row.has_policy = route.has_policy
        row.policy_enabled = route.policy_enabled

        policy = _normalize_content_policy(route.content_policy)
        row.allow_text = policy.allow_text
        row.allow_images = policy.allow_images
        row.allow_video = policy.allow_video
        row.allow_audio = policy.allow_audio
        row.allow_documents = policy.allow_documents
        row.allow_reposts = policy.allow_reposts
        row.max_images = policy.max_images
        row.max_video_size_mb = policy.max_video_size_mb
        row.max_audio_size_mb = policy.max_audio_size_mb
        row.drop_unsupported_media = policy.drop_unsupported_media
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
                )
                .order_by(RouteORM.id)
            )
        ).scalars().all()
        matched = []
        for row in rows:
            if row.source_platform == "telegram":
                route_canonical = row.source_chat_canonical or canonicalize_telegram_chat_ref(row.source_chat_id)
                incoming_canonical = canonicalize_telegram_chat_ref(source_chat_id)
                if route_canonical != incoming_canonical:
                    continue
            else:
                if str(row.source_chat_id) != str(source_chat_id):
                    continue
            matched.append(row)
        return [orm_to_route(row) for row in matched]
