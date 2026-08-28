from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv

from .bot.app import build_bot, build_dispatcher
from .bot.notifier import Notifier
from .config import ConfigManager
from .userbot import Userbot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run() -> None:
    load_dotenv()

    api_id = int(os.environ["API_ID"])
    api_hash = os.environ["API_HASH"]
    bot_token = os.environ["BOT_TOKEN"]

    admin_ids = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]
    if not admin_ids:
        raise SystemExit("ADMIN_IDS не задан в .env - укажите хотя бы один Telegram ID")

    session_name = os.environ.get("SESSION_NAME", "data/userbot")
    config_path = os.environ.get("CONFIG_PATH", "data/config.json")

    config_manager = ConfigManager(config_path)

    bot = build_bot(bot_token)
    notifier = Notifier(bot, admin_ids)
    userbot = Userbot(session_name, api_id, api_hash, config_manager, notifier)

    dp = build_dispatcher(admin_ids)
    dp["config_manager"] = config_manager
    dp["userbot"] = userbot

    await userbot.start()

    if not await userbot.client.is_user_authorized():
        logger.warning(
            "Сессия аккаунта-наблюдателя не авторизована. Запустите `python scripts/login.py`, "
            "прежде чем чаты начнут мониториться."
        )

    try:
        await asyncio.gather(
            dp.start_polling(bot),
            userbot.run_until_disconnected(),
        )
    finally:
        await bot.session.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
