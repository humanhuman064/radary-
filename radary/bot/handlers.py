from __future__ import annotations

import json
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from telethon.utils import get_display_name, get_peer_id

from ..config import AppConfig, ChatEntry, ConfigManager
from ..userbot import Userbot
from .keyboards import cancel_menu, chats_menu, main_menu, word_list_menu
from .states import AddChat, AddKeywords, AddStopWords, ImportConfig

logger = logging.getLogger(__name__)
router = Router()


def _menu_text(cfg: AppConfig) -> str:
    state = "🟢 включен" if cfg.monitoring_enabled else "🔴 выключен"
    return (
        "<b>Radary</b> — мониторинг чатов по ключевым словам\n\n"
        f"Мониторинг: {state}\n"
        f"Чатов: {len(cfg.chats)}\n"
        f"Ключевых слов: {len(cfg.keywords)}\n"
        f"Стоп-слов: {len(cfg.stop_words)}"
    )


@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start(message: Message, state: FSMContext, config_manager: ConfigManager) -> None:
    await state.clear()
    cfg = config_manager.get()
    await message.answer(_menu_text(cfg), reply_markup=main_menu(cfg))


@router.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery, state: FSMContext, config_manager: ConfigManager) -> None:
    await state.clear()
    cfg = config_manager.get()
    await callback.message.edit_text(_menu_text(cfg), reply_markup=main_menu(cfg))
    await callback.answer()


@router.callback_query(F.data == "toggle_monitoring")
async def cb_toggle_monitoring(callback: CallbackQuery, config_manager: ConfigManager) -> None:
    cfg = config_manager.get().model_copy(deep=True)
    cfg.monitoring_enabled = not cfg.monitoring_enabled
    await config_manager.save(cfg)
    await callback.message.edit_text(_menu_text(cfg), reply_markup=main_menu(cfg))
    await callback.answer("Мониторинг включен" if cfg.monitoring_enabled else "Мониторинг выключен")


@router.callback_query(F.data == "status")
async def cb_status(callback: CallbackQuery, config_manager: ConfigManager, userbot: Userbot) -> None:
    cfg = config_manager.get()
    authorized = await userbot.client.is_user_authorized()
    text = _menu_text(cfg) + "\n\n" + (
        "✅ Аккаунт-наблюдатель подключен"
        if authorized
        else "⚠️ Аккаунт не авторизован. Запустите scripts/login.py на сервере."
    )
    await callback.message.edit_text(text, reply_markup=main_menu(cfg))
    await callback.answer()


# --- Chats ---

@router.callback_query(F.data == "menu_chats")
async def cb_menu_chats(callback: CallbackQuery, config_manager: ConfigManager) -> None:
    cfg = config_manager.get()
    await callback.message.edit_text("💬 Отслеживаемые чаты:", reply_markup=chats_menu(cfg))
    await callback.answer()


@router.callback_query(F.data == "add_chat")
async def cb_add_chat(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddChat.waiting_input)
    await callback.message.edit_text(
        "Отправьте @username чата, его ID или ссылку t.me/... для добавления в мониторинг.\n\n"
        "Важно: аккаунт-наблюдатель должен уже состоять в этом чате.",
        reply_markup=cancel_menu(),
    )
    await callback.answer()


def _parse_chat_identifier(text: str):
    text = text.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    text = text.lstrip("@")
    try:
        return int(text)
    except ValueError:
        return text


@router.message(AddChat.waiting_input)
async def on_add_chat_input(
    message: Message, state: FSMContext, config_manager: ConfigManager, userbot: Userbot
) -> None:
    if not message.text:
        await message.answer("Отправьте текстом @username, ID или ссылку на чат.")
        return

    identifier = _parse_chat_identifier(message.text)
    try:
        entity = await userbot.resolve_chat(identifier)
    except Exception as exc:
        logger.warning("Failed to resolve chat %r: %s", identifier, exc)
        await message.answer(
            "Не удалось найти этот чат. Убедитесь, что аккаунт-наблюдатель уже состоит в нём "
            "и что username/ID указан верно."
        )
        return

    chat_id = get_peer_id(entity)
    title = get_display_name(entity) or getattr(entity, "username", "") or str(chat_id)
    username = getattr(entity, "username", None)

    cfg = config_manager.get().model_copy(deep=True)
    if any(c.id == chat_id for c in cfg.chats):
        await message.answer(f"Чат «{title}» уже отслеживается.")
    else:
        cfg.chats.append(ChatEntry(id=chat_id, title=title, username=username))
        await config_manager.save(cfg)
        await message.answer(f"Чат «{title}» добавлен в мониторинг.")

    await state.clear()
    await message.answer("💬 Отслеживаемые чаты:", reply_markup=chats_menu(config_manager.get()))


@router.callback_query(F.data.startswith("del_chat:"))
async def cb_del_chat(callback: CallbackQuery, config_manager: ConfigManager) -> None:
    chat_id = int(callback.data.split(":", 1)[1])
    cfg = config_manager.get().model_copy(deep=True)
    cfg.chats = [c for c in cfg.chats if c.id != chat_id]
    await config_manager.save(cfg)
    await callback.message.edit_text("💬 Отслеживаемые чаты:", reply_markup=chats_menu(cfg))
    await callback.answer("Чат удалён")


# --- Keywords / stop-words ---

async def _show_word_list(callback: CallbackQuery, cfg: AppConfig, prefix: str) -> None:
    title = "🔑 Ключевые слова:" if prefix == "kw" else "🚫 Стоп-слова:"
    words = cfg.keywords if prefix == "kw" else cfg.stop_words
    await callback.message.edit_text(title, reply_markup=word_list_menu(words, prefix))


@router.callback_query(F.data == "menu_keywords")
async def cb_menu_keywords(callback: CallbackQuery, config_manager: ConfigManager) -> None:
    await _show_word_list(callback, config_manager.get(), "kw")
    await callback.answer()


@router.callback_query(F.data == "menu_stopwords")
async def cb_menu_stopwords(callback: CallbackQuery, config_manager: ConfigManager) -> None:
    await _show_word_list(callback, config_manager.get(), "sw")
    await callback.answer()


@router.callback_query(F.data == "add_kw")
async def cb_add_kw(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddKeywords.waiting_input)
    await callback.message.edit_text(
        "Отправьте ключевые слова, каждое с новой строки.", reply_markup=cancel_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "add_sw")
async def cb_add_sw(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddStopWords.waiting_input)
    await callback.message.edit_text(
        "Отправьте стоп-слова, каждое с новой строки.", reply_markup=cancel_menu()
    )
    await callback.answer()


async def _handle_add_words(
    message: Message, state: FSMContext, config_manager: ConfigManager, prefix: str
) -> None:
    if not message.text:
        await message.answer("Отправьте слова текстом, каждое с новой строки.")
        return

    new_words = [line.strip() for line in message.text.splitlines() if line.strip()]
    cfg = config_manager.get().model_copy(deep=True)
    target = cfg.keywords if prefix == "kw" else cfg.stop_words
    existing_lower = {w.lower() for w in target}
    added = 0
    for w in new_words:
        if w.lower() not in existing_lower:
            target.append(w)
            existing_lower.add(w.lower())
            added += 1

    await config_manager.save(cfg)
    await state.clear()

    label = "ключевых слов" if prefix == "kw" else "стоп-слов"
    await message.answer(f"Добавлено {added} {label}.")

    cfg = config_manager.get()
    words = cfg.keywords if prefix == "kw" else cfg.stop_words
    title = "🔑 Ключевые слова:" if prefix == "kw" else "🚫 Стоп-слова:"
    await message.answer(title, reply_markup=word_list_menu(words, prefix))


@router.message(AddKeywords.waiting_input)
async def on_add_keywords(message: Message, state: FSMContext, config_manager: ConfigManager) -> None:
    await _handle_add_words(message, state, config_manager, "kw")


@router.message(AddStopWords.waiting_input)
async def on_add_stopwords(message: Message, state: FSMContext, config_manager: ConfigManager) -> None:
    await _handle_add_words(message, state, config_manager, "sw")


async def _del_word(callback: CallbackQuery, config_manager: ConfigManager, prefix: str) -> None:
    idx = int(callback.data.split(":", 1)[1])
    cfg = config_manager.get().model_copy(deep=True)
    target = cfg.keywords if prefix == "kw" else cfg.stop_words
    if 0 <= idx < len(target):
        target.pop(idx)
        await config_manager.save(cfg)
    await _show_word_list(callback, cfg, prefix)
    await callback.answer("Удалено")


@router.callback_query(F.data.startswith("del_kw:"))
async def cb_del_kw(callback: CallbackQuery, config_manager: ConfigManager) -> None:
    await _del_word(callback, config_manager, "kw")


@router.callback_query(F.data.startswith("del_sw:"))
async def cb_del_sw(callback: CallbackQuery, config_manager: ConfigManager) -> None:
    await _del_word(callback, config_manager, "sw")


async def _clear_words(callback: CallbackQuery, config_manager: ConfigManager, prefix: str) -> None:
    cfg = config_manager.get().model_copy(deep=True)
    if prefix == "kw":
        cfg.keywords = []
    else:
        cfg.stop_words = []
    await config_manager.save(cfg)
    await _show_word_list(callback, cfg, prefix)
    await callback.answer("Список очищен")


@router.callback_query(F.data == "clear_kw")
async def cb_clear_kw(callback: CallbackQuery, config_manager: ConfigManager) -> None:
    await _clear_words(callback, config_manager, "kw")


@router.callback_query(F.data == "clear_sw")
async def cb_clear_sw(callback: CallbackQuery, config_manager: ConfigManager) -> None:
    await _clear_words(callback, config_manager, "sw")


# --- Config import/export ---

@router.callback_query(F.data == "export_config")
async def cb_export_config(callback: CallbackQuery, config_manager: ConfigManager) -> None:
    cfg = config_manager.get()
    data = json.dumps(cfg.model_dump(), ensure_ascii=False, indent=2).encode("utf-8")
    await callback.message.answer_document(BufferedInputFile(data, filename="config.json"))
    await callback.answer()


@router.callback_query(F.data == "import_config")
async def cb_import_config(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ImportConfig.waiting_file)
    await callback.message.edit_text(
        "Отправьте файл config.json для замены текущих настроек чатов, ключевых и стоп-слов.",
        reply_markup=cancel_menu(),
    )
    await callback.answer()


@router.message(ImportConfig.waiting_file, F.document)
async def on_import_config(
    message: Message, state: FSMContext, config_manager: ConfigManager, bot: Bot
) -> None:
    document = message.document
    if not document.file_name or not document.file_name.endswith(".json"):
        await message.answer("Нужен файл в формате .json")
        return

    file = await bot.get_file(document.file_id)
    buf = await bot.download_file(file.file_path)
    try:
        data = json.loads(buf.read().decode("utf-8"))
        cfg = AppConfig.model_validate(data)
    except Exception as exc:
        await message.answer(f"Не удалось прочитать файл: {exc}")
        return

    await config_manager.save(cfg)
    await state.clear()
    await message.answer("Конфигурация обновлена.")
    await message.answer(_menu_text(cfg), reply_markup=main_menu(cfg))


@router.message(ImportConfig.waiting_file)
async def on_import_config_wrong_type(message: Message) -> None:
    await message.answer("Пришлите файл config.json документом (не текстом и не фото).")
