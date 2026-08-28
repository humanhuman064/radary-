from __future__ import annotations

from typing import List

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..config import AppConfig


def main_menu(cfg: AppConfig) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    toggle_text = "⏸ Остановить мониторинг" if cfg.monitoring_enabled else "▶️ Запустить мониторинг"
    b.button(text=toggle_text, callback_data="toggle_monitoring")
    b.button(text=f"💬 Чаты ({len(cfg.chats)})", callback_data="menu_chats")
    b.button(text=f"🔑 Ключевые слова ({len(cfg.keywords)})", callback_data="menu_keywords")
    b.button(text=f"🚫 Стоп-слова ({len(cfg.stop_words)})", callback_data="menu_stopwords")
    b.button(text="📄 Экспорт конфига", callback_data="export_config")
    b.button(text="📥 Импорт конфига", callback_data="import_config")
    b.button(text="ℹ️ Статус", callback_data="status")
    b.adjust(1, 1, 1, 1, 2, 1)
    return b.as_markup()


def cancel_menu() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Отмена", callback_data="back_main")
    return b.as_markup()


def chats_menu(cfg: AppConfig) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for chat in cfg.chats:
        label = chat.title or str(chat.id)
        if len(label) > 30:
            label = label[:27] + "..."
        b.button(text=f"❌ {label}", callback_data=f"del_chat:{chat.id}")
    b.button(text="➕ Добавить чат", callback_data="add_chat")
    b.button(text="⬅️ Назад", callback_data="back_main")
    b.adjust(1)
    return b.as_markup()


def word_list_menu(words: List[str], prefix: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for i, w in enumerate(words):
        label = w if len(w) <= 30 else w[:27] + "..."
        b.button(text=f"❌ {label}", callback_data=f"del_{prefix}:{i}")
    b.button(text="➕ Добавить", callback_data=f"add_{prefix}")
    if words:
        b.button(text="🗑 Очистить всё", callback_data=f"clear_{prefix}")
    b.button(text="⬅️ Назад", callback_data="back_main")
    b.adjust(1)
    return b.as_markup()
