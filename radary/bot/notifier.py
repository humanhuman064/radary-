from __future__ import annotations

import logging
from io import BytesIO
from typing import List

from aiogram import Bot
from aiogram.types import BufferedInputFile

logger = logging.getLogger(__name__)

MAX_CAPTION = 1024
MAX_MESSAGE = 4096


def build_message_link(chat, message_id: int) -> str:
    username = getattr(chat, "username", None)
    if username:
        return f"https://t.me/{username}/{message_id}"

    chat_id = getattr(chat, "id", None)
    if chat_id is None:
        return ""
    internal = str(chat_id)
    if internal.startswith("-100"):
        internal = internal[4:]
    elif internal.startswith("-"):
        internal = internal[1:]
    return f"https://t.me/c/{internal}/{message_id}"


def _sender_label(sender) -> str:
    if sender is None:
        return "неизвестно"
    username = getattr(sender, "username", None)
    first = getattr(sender, "first_name", "") or ""
    last = getattr(sender, "last_name", "") or ""
    title = getattr(sender, "title", None)
    name = title or " ".join(p for p in (first, last) if p) or "без имени"
    return f"{name} (@{username})" if username else name


class Notifier:
    """Formats matched Telethon messages and delivers them via the aiogram Bot."""

    def __init__(self, bot: Bot, admin_ids: List[int]):
        self.bot = bot
        self.admin_ids = admin_ids

    async def send_alert(self, event, matched_keywords: List[str]) -> None:
        message = event.message

        try:
            chat = await event.get_chat()
        except Exception:
            chat = None
        try:
            sender = await event.get_sender()
        except Exception:
            sender = None

        chat_title = (
            getattr(chat, "title", None)
            or getattr(chat, "first_name", None)
            or "Личное сообщение"
        )
        link = build_message_link(chat, message.id) if chat is not None else ""

        header = (
            "🔔 <b>Найдено совпадение</b>\n"
            f"💬 Чат: {chat_title}\n"
            f"👤 От: {_sender_label(sender)}\n"
            f"🔑 Слова: {', '.join(matched_keywords)}\n"
        )
        if link:
            header += f'🔗 <a href="{link}">Открыть сообщение</a>\n'

        text = event.raw_text or ""

        for admin_id in self.admin_ids:
            try:
                await self._deliver(admin_id, message, header, text)
            except Exception:
                logger.exception("Failed to deliver alert to %s", admin_id)

    async def _deliver(self, admin_id: int, message, header: str, text: str) -> None:
        has_media = bool(
            message.photo or message.video or message.document or message.audio or message.voice
        )

        if not has_media:
            full = (header + "\n" + text).strip()
            await self.bot.send_message(admin_id, full[:MAX_MESSAGE], parse_mode="HTML")
            return

        buf = BytesIO()
        await message.client.download_media(message, file=buf)
        buf.seek(0)

        filename = "file"
        if message.document and message.document.attributes:
            for attr in message.document.attributes:
                fname = getattr(attr, "file_name", None)
                if fname:
                    filename = fname
                    break

        caption = (header + "\n" + text).strip()[:MAX_CAPTION]
        input_file = BufferedInputFile(buf.read(), filename=filename)

        if message.photo:
            await self.bot.send_photo(admin_id, input_file, caption=caption, parse_mode="HTML")
        elif message.video:
            await self.bot.send_video(admin_id, input_file, caption=caption, parse_mode="HTML")
        else:
            await self.bot.send_document(admin_id, input_file, caption=caption, parse_mode="HTML")

        if len(header + text) > MAX_CAPTION:
            await self.bot.send_message(
                admin_id, (header + "\n" + text).strip()[:MAX_MESSAGE], parse_mode="HTML"
            )
