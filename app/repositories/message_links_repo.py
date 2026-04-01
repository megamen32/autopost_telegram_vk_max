from sqlalchemy import select

from app.db.models import MessageLinkORM
from app.repositories.base import SQLAlchemyRepo


class MessageLinksRepo(SQLAlchemyRepo):
    async def create(
        self,
        origin_platform: str,
        origin_chat_id: str,
        origin_message_id: str,
        target_platform: str,
        target_chat_id: str,
        target_message_id: str,
    ) -> dict:
        row = MessageLinkORM(
            origin_platform=origin_platform,
            origin_chat_id=origin_chat_id,
            origin_message_id=origin_message_id,
            target_platform=target_platform,
            target_chat_id=target_chat_id,
            target_message_id=target_message_id,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return {
            "id": row.id,
            "origin_platform": row.origin_platform,
            "origin_chat_id": row.origin_chat_id,
            "origin_message_id": row.origin_message_id,
            "target_platform": row.target_platform,
            "target_chat_id": row.target_chat_id,
            "target_message_id": row.target_message_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    async def list_all(self) -> list[dict]:
        rows = (await self.session.execute(select(MessageLinkORM).order_by(MessageLinkORM.id))).scalars().all()
        return [
            {
                "id": row.id,
                "origin_platform": row.origin_platform,
                "origin_chat_id": row.origin_chat_id,
                "origin_message_id": row.origin_message_id,
                "target_platform": row.target_platform,
                "target_chat_id": row.target_chat_id,
                "target_message_id": row.target_message_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
