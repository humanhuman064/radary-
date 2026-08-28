from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class ChatEntry(BaseModel):
    id: int
    title: str = ""
    username: Optional[str] = None


class AppConfig(BaseModel):
    chats: List[ChatEntry] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    stop_words: List[str] = Field(default_factory=list)
    monitoring_enabled: bool = True


class ConfigManager:
    """Keeps AppConfig in memory and persists it to a JSON file on every change."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = asyncio.Lock()
        self._config = self._load()

    def _load(self) -> AppConfig:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return AppConfig.model_validate(data)
        cfg = AppConfig()
        self._write(cfg)
        return cfg

    def _write(self, cfg: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(cfg.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self) -> AppConfig:
        return self._config

    async def save(self, cfg: AppConfig) -> None:
        async with self._lock:
            self._config = cfg
            self._write(cfg)
