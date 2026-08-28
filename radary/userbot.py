from __future__ import annotations

import logging
from typing import Union

from telethon import TelegramClient, events
from telethon.tl.types import TypeInputPeer

from .config import ConfigManager
from .filters import should_forward

logger = logging.getLogger(__name__)


class Userbot:
    """Wraps a Telethon client that monitors chats on behalf of the configured account."""

    def __init__(
        self,
        session_path: str,
        api_id: int,
        api_hash: str,
        config_manager: ConfigManager,
        notifier,
    ):
        self.client = TelegramClient(session_path, api_id, api_hash)
        self.config_manager = config_manager
        self.notifier = notifier

    async def start(self) -> None:
        await self.client.start()
        if await self.client.is_user_authorized():
            me = await self.client.get_me()
            label = getattr(me, "username", None) or me.first_name
            logger.info("Userbot authorized as %s (id=%s)", label, me.id)
        self.client.add_event_handler(self._on_new_message, events.NewMessage(incoming=True))

    async def run_until_disconnected(self) -> None:
        await self.client.run_until_disconnected()

    async def resolve_chat(self, identifier: Union[str, int]) -> TypeInputPeer:
        return await self.client.get_entity(identifier)

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        cfg = self.config_manager.get()
        if not cfg.monitoring_enabled or not cfg.chats:
            return

        monitored_ids = {c.id for c in cfg.chats}
        if event.chat_id not in monitored_ids:
            return

        text = event.raw_text or ""
        forward, matched = should_forward(text, cfg.keywords, cfg.stop_words)
        if not forward:
            return

        try:
            await self.notifier.send_alert(event, matched)
        except Exception:
            logger.exception("Failed to send alert for message %s", event.message.id)
