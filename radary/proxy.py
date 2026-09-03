from __future__ import annotations

from typing import Optional, Tuple
from urllib.parse import urlsplit

SUPPORTED_SCHEMES = ("socks5", "socks4", "http")

TelethonProxy = Tuple[str, str, int, bool, Optional[str], Optional[str]]


def parse_proxy_url(url: str) -> Optional[TelethonProxy]:
    """Parse a proxy URL (socks5://user:pass@host:port) into the tuple format Telethon expects.

    Returns None for an empty URL. Raises ValueError for anything malformed.
    """
    url = url.strip()
    if not url:
        return None

    parts = urlsplit(url)
    scheme = parts.scheme.lower()
    if scheme not in SUPPORTED_SCHEMES:
        raise ValueError(
            f"Неизвестная схема прокси {parts.scheme!r}. "
            f"Используйте одну из: {', '.join(SUPPORTED_SCHEMES)}"
        )
    if not parts.hostname or not parts.port:
        raise ValueError(
            "PROXY_URL должен содержать хост и порт, например socks5://user:pass@1.2.3.4:1080"
        )

    return (scheme, parts.hostname, parts.port, True, parts.username, parts.password)
