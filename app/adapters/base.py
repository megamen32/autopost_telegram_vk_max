from abc import ABC, abstractmethod

from app.domain.enums import Platform
from app.domain.models import UnifiedPost


class BaseAdapter(ABC):
    platform: Platform

    @abstractmethod
    async def parse_incoming_event(self, payload: dict) -> UnifiedPost | None:
        raise NotImplementedError

    @abstractmethod
    async def publish_post(self, chat_id: str, post: UnifiedPost) -> str:
        raise NotImplementedError

    @abstractmethod
    async def delete_post(self, chat_id: str, message_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def edit_post(self, chat_id: str, message_id: str, post: UnifiedPost) -> None:
        raise NotImplementedError

    @abstractmethod
    async def supports_feature(self, feature: str) -> bool:
        raise NotImplementedError
