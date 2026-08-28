"""Одноразовый интерактивный вход в аккаунт-наблюдатель.

Запустите этот скрипт один раз из терминала (локально или на сервере) перед
первым стартом основного приложения. Он спросит номер телефона, код
подтверждения, присланный в Telegram, и пароль двухфакторной аутентификации
(если он включен). После этого будет создан .session-файл рядом с путём
из SESSION_NAME - храните его в секрете, он даёт полный доступ к аккаунту.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient


async def main() -> None:
    load_dotenv()
    api_id = int(os.environ["API_ID"])
    api_hash = os.environ["API_HASH"]
    session_name = os.environ.get("SESSION_NAME", "data/userbot")
    Path(session_name).parent.mkdir(parents=True, exist_ok=True)

    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()
    me = await client.get_me()
    print(f"Успешно вошли как {me.first_name} (id={me.id}). Сессия сохранена в {session_name}.session")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
