"""
ATLAS Session Manager — updated to include MarketMemory per session.
Memory instance is created with each new session and persists until timeout or /start.
"""

import time
import logging
from config import SESSION_TIMEOUT_SECONDS, MAX_HISTORY_MESSAGES

logger = logging.getLogger(__name__)

try:
    from memory import MarketMemory
    _MEMORY_AVAILABLE = True
except ImportError:
    _MEMORY_AVAILABLE = False
    logger.warning("memory.py not found — sessions will run without memory.")

# Structure: { chat_id: { lang, warned, history, last_active, memory } }

_sessions = {}


def _new_session() -> dict:
    return {
        "lang": "id",
        "warned": False,
        "history": [],
        "last_active": time.time(),
        "memory": MarketMemory() if _MEMORY_AVAILABLE else None,
    }


def get_session(chat_id: int) -> dict:
    """Get session for chat_id, auto-reset if expired."""
    now = time.time()
    session = _sessions.get(chat_id)

    if session and (now - session["last_active"]) > SESSION_TIMEOUT_SECONDS:
        logger.info(f"Session expired for chat_id={chat_id} — resetting")
        _sessions[chat_id] = _new_session()

    if chat_id not in _sessions:
        _sessions[chat_id] = _new_session()

    return _sessions[chat_id]


def reset_session(chat_id: int):
    """Reset session — called on /start or timeout."""
    _sessions[chat_id] = _new_session()


def update_last_active(chat_id: int):
    session = get_session(chat_id)
    session["last_active"] = time.time()


def add_to_history(chat_id: int, role: str, content: str):
    """Append message to history, keep max limit."""
    session = get_session(chat_id)
    session["history"].append({"role": role, "content": content})
    if len(session["history"]) > MAX_HISTORY_MESSAGES:
        session["history"] = session["history"][-MAX_HISTORY_MESSAGES:]


def set_lang(chat_id: int, lang: str):
    get_session(chat_id)["lang"] = lang


def set_warned(chat_id: int):
    get_session(chat_id)["warned"] = True
