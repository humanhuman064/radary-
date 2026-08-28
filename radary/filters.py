from __future__ import annotations

from typing import Iterable, List, Tuple


def _contains_any(text_lower: str, words: Iterable[str]) -> List[str]:
    return [w for w in words if w and w.lower() in text_lower]


def should_forward(text: str, keywords: List[str], stop_words: List[str]) -> Tuple[bool, List[str]]:
    """Decide whether a message should be forwarded.

    Stop-words take priority: if any stop-word is found the message is
    never forwarded, even if it also matches a keyword.
    """
    if not text:
        return False, []

    text_lower = text.lower()

    if _contains_any(text_lower, stop_words):
        return False, []

    matched = _contains_any(text_lower, keywords)
    return bool(matched), matched
