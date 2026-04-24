import re
import logging
from groq_client import call_groq
from prompts import get_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)

# Known tickers for basic validation
KNOWN_TICKERS = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "MATIC", "DOGE",
    "BBCA", "BBRI", "TLKM", "GOTO", "BMRI", "ASII",
    "AAPL", "NVDA", "TSLA", "META", "MSFT",
    "XAUUSD", "DXY", "EURUSD",
}

OUT_OF_SCOPE_PATTERNS = [
    r"\bbeli\b", r"\bjual\b", r"\bkapan naik\b", r"\bkapan turun\b",
    r"\bbalik modal\b", r"\bprofit\b", r"\buntung\b",
    r"\bbuy\b", r"\bsell\b", r"\bwhen.*moon\b",
]


def extract_ticker(text: str) -> str | None:
    """Extract ticker from user input. Returns uppercase ticker or None."""
    words = text.upper().split()
    for word in words:
        clean = re.sub(r"[^A-Z]", "", word)
        if clean in KNOWN_TICKERS:
            return clean
    return None


def is_out_of_scope(text: str) -> bool:
    """Check if input is asking for signals or profit guarantees."""
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in OUT_OF_SCOPE_PATTERNS)


def run_analysis(user_text: str, history: list, lang: str) -> str:
    """
    Main analysis function.
    Returns formatted text ready to send to Telegram.
    """
    # Guard: out of scope
    if is_out_of_scope(user_text):
        # Handled in bot.py before reaching here, but double-check
        return None

    ticker = extract_ticker(user_text)
    system_prompt = get_system_prompt(lang)
    user_prompt = build_user_prompt(user_text, ticker)

    # Build messages: history + current user message
    messages = history + [{"role": "user", "content": user_prompt}]

    logger.info(f"Running analysis | ticker={ticker} | lang={lang}")
    result = call_groq(system_prompt, messages)
    return result
