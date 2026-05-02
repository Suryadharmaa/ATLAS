"""ATLAS Analyzer — ticker extraction, scope check, analysis routing."""

import re
import logging
from groq_client import call_groq
from prompts import get_system_prompt, build_user_prompt
from market_data import fetch_market_snapshot, format_snapshot_for_prompt
from debater import run_debate

logger = logging.getLogger(__name__)

KNOWN_TICKERS = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "MATIC", "DOGE",
    "BBCA", "BBRI", "TLKM", "GOTO", "BMRI", "ASII",
    "AAPL", "NVDA", "TSLA", "META", "MSFT",
    "XAUUSD", "DXY", "EURUSD",
}

OUT_OF_SCOPE_PATTERNS = [
    r"\bbeli\b", r"\bjual\b", r"\bkapan naik\b", r"\bkapan turun\b",
    r"\bbalik modal\b", r"\buntung\b",
    r"\bbuy\b", r"\bsell\b", r"\bwhen.*moon\b",
]


def extract_ticker(text: str) -> str | None:
    words = text.upper().split()
    for word in words:
        clean = re.sub(r"[^A-Z]", "", word)
        if clean in KNOWN_TICKERS:
            return clean
    return None


def is_out_of_scope(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in OUT_OF_SCOPE_PATTERNS)


def run_analysis(user_text: str, history: list, lang: str, memory=None) -> str | None:
    if is_out_of_scope(user_text):
        return None
    ticker = extract_ticker(user_text)
    if ticker:
        snapshot = fetch_market_snapshot(ticker)
        market_str = format_snapshot_for_prompt(snapshot)
        memory_context = ""
        if memory and len(memory) > 0:
            situation_key = (
                f"{ticker} RSI:{snapshot.get('rsi')} MACD:{snapshot.get('macd')} change7d:{snapshot.get('change_7d_pct')}"
                if snapshot else f"{ticker} {user_text[:60]}"
            )
            past = memory.recall(situation_key, n=1)
            if past:
                memory_context = past[0]["summary"]
        result = run_debate(
            ticker=ticker, market_data_str=market_str, user_text=user_text,
            history=history, lang=lang, memory_context=memory_context,
        )
        if result and memory and snapshot:
            situation_key = f"{ticker} RSI:{snapshot.get('rsi')} MACD:{snapshot.get('macd')} change7d:{snapshot.get('change_7d_pct')}"
            memory.add(situation_key, result)
        if result:
            return result
        logger.warning(f"Debate fallback for {ticker}")
        system_prompt = get_system_prompt(lang)
        enriched_text = f"{user_text}\n\n{market_str}"
        user_prompt = build_user_prompt(enriched_text, ticker)
        messages = history + [{"role": "user", "content": user_prompt}]
        return call_groq(system_prompt, messages)
    logger.info("run_analysis | no ticker | single-call mode")
    system_prompt = get_system_prompt(lang)
    user_prompt = build_user_prompt(user_text)
    messages = history + [{"role": "user", "content": user_prompt}]
    return call_groq(system_prompt, messages)
