from sqlalchemy import select

from app.db.models import ProcessedEventORM
from app.repositories.base import SQLAlchemyRepo


class ProcessedEventsRepo(SQLAlchemyRepo):
    async def exists(self, source_platform: str, source_chat_id: str, source_message_id: str) -> bool:
        row = (
            await self.session.execute(
                select(ProcessedEventORM.id).where(
                    ProcessedEventORM.source_platform == source_platform,
                    ProcessedEventORM.source_chat_id == source_chat_id,
                    ProcessedEventORM.source_message_id == source_message_id,
                )
            )
        ).scalar_one_or_none()
        return row is not None

    async def create(self, source_platform: str, source_chat_id: str, source_message_id: str, content_hash: str) -> None:
        self.session.add(
            ProcessedEventORM(
                source_platform=source_platform,
                source_chat_id=source_chat_id,
                source_message_id=source_message_id,
                content_hash=content_hash,
            )
        )
        await self.session.commit()

    async def list_all(self) -> list[dict]:
        rows = (await self.session.execute(select(ProcessedEventORM).order_by(ProcessedEventORM.id))).scalars().all()
        return [
            {
                "id": row.id,
                "source_platform": row.source_platform,
                "source_chat_id": row.source_chat_id,
                "source_message_id": row.source_message_id,
                "content_hash": row.content_hash,
                "processed_at": row.processed_at.isoformat() if row.processed_at else None,
            }
            for row in rows
        ]
