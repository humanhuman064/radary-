from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Iterable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class AdminOnlyMiddleware(BaseMiddleware):
    """Silently drops any update from a user not listed in ADMIN_IDS."""

    def __init__(self, admin_ids: Iterable[int]):
        self.admin_ids = set(admin_ids)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None or user.id not in self.admin_ids:
            return None
        return await handler(event, data)
