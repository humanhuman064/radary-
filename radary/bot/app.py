from __future__ import annotations

from typing import List, Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from .handlers import router
from .middlewares import AdminOnlyMiddleware


def build_dispatcher(admin_ids: List[int]) -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)

    admin_mw = AdminOnlyMiddleware(admin_ids)
    dp.message.outer_middleware(admin_mw)
    dp.callback_query.outer_middleware(admin_mw)

    return dp


def build_bot(token: str, proxy_url: Optional[str] = None) -> Bot:
    session = AiohttpSession(proxy=proxy_url) if proxy_url else None
    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )
