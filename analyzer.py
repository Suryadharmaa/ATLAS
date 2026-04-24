“””
ATLAS Analyzer — updated to integrate:

- market_data.py  : real yfinance OHLCV + technical indicators
- debater.py      : Bull/Bear debate → synthesis (adapted from TradingAgents)
- memory.py       : BM25 recall for session context enrichment

Flow:

1. Validate input (scope check, ticker extraction)
1. Fetch real market data (yfinance)
1. Recall relevant past analysis (BM25 memory)
1. Run Bull/Bear debate → synthesis (debater)
1. Fallback to single-call if ticker missing or debate fails
   “””

import re
import logging
from groq_client import call_groq
from prompts import get_system_prompt, build_user_prompt
from market_data import fetch_market_snapshot, format_snapshot_for_prompt
from debater import run_debate

logger = logging.getLogger(**name**)

# ─── Known Tickers ────────────────────────────────────────────────────────────

KNOWN_TICKERS = {
# Crypto
“BTC”, “ETH”, “SOL”, “BNB”, “XRP”, “MATIC”, “DOGE”,
# IDX
“BBCA”, “BBRI”, “TLKM”, “GOTO”, “BMRI”, “ASII”,
# US Stocks
“AAPL”, “NVDA”, “TSLA”, “META”, “MSFT”,
# Forex & Metals
“XAUUSD”, “DXY”, “EURUSD”,
}

# ─── Out-of-Scope Patterns ────────────────────────────────────────────────────

OUT_OF_SCOPE_PATTERNS = [
r”\bbeli\b”, r”\bjual\b”, r”\bkapan naik\b”, r”\bkapan turun\b”,
r”\bbalik modal\b”, r”\buntung\b”,
r”\bbuy\b”, r”\bsell\b”, r”\bwhen.*moon\b”,
# “profit” removed — it’s ambiguous and blocks legitimate analysis questions
]

def extract_ticker(text: str) -> str | None:
“”“Extract a known ticker from user input. Returns uppercase or None.”””
words = text.upper().split()
for word in words:
clean = re.sub(r”[^A-Z]”, “”, word)
if clean in KNOWN_TICKERS:
return clean
return None

def is_out_of_scope(text: str) -> bool:
“”“True if input is asking for signals, not analysis context.”””
text_lower = text.lower()
return any(re.search(p, text_lower) for p in OUT_OF_SCOPE_PATTERNS)

def run_analysis(
user_text: str,
history: list,
lang: str,
memory=None,       # MarketMemory instance from session (optional)
) -> str | None:
“””
Main analysis entry point.

```
If ticker identified → enhanced path: market data + debate + memory.
No ticker → fallback: single Groq call with system prompt only.

Returns formatted string ready for post_process() → Telegram.
Returns None if out-of-scope (handled upstream in bot.py).
"""

if is_out_of_scope(user_text):
    return None

ticker = extract_ticker(user_text)

# ── Path A: Ticker found — full enhanced analysis ─────────────────────────
if ticker:
    # Step 1: Real market data
    snapshot = fetch_market_snapshot(ticker)
    market_str = format_snapshot_for_prompt(snapshot)
    data_available = snapshot is not None

    logger.info(
        f"run_analysis | ticker={ticker} | data={'OK' if data_available else 'N/A'} | lang={lang}"
    )

    # Step 2: Memory recall — inject past context if available
    memory_context = ""
    if memory and len(memory) > 0:
        situation_key = (
            f"{ticker} RSI:{snapshot.get('rsi')} "
            f"MACD:{snapshot.get('macd')} "
            f"change7d:{snapshot.get('change_7d_pct')}"
            if snapshot else f"{ticker} {user_text[:60]}"
        )
        past = memory.recall(situation_key, n=1)
        if past:
            memory_context = past[0]["summary"]
            logger.info(f"Memory recall hit | score={past[0]['score']}")

    # Step 3: Bull/Bear debate → synthesis
    result = run_debate(
        ticker=ticker,
        market_data_str=market_str,
        user_text=user_text,
        history=history,
        lang=lang,
        memory_context=memory_context,
    )

    # Step 4: Store this analysis in memory for future sessions
    if result and memory and snapshot:
        situation_key = (
            f"{ticker} RSI:{snapshot.get('rsi')} "
            f"MACD:{snapshot.get('macd')} "
            f"change7d:{snapshot.get('change_7d_pct')}"
        )
        memory.add(situation_key, result)

    if result:
        return result

    # Debate failed — fallback to single call with market data injected
    logger.warning(f"Debate fallback for {ticker}")
    system_prompt = get_system_prompt(lang)
    enriched_text = f"{user_text}\n\n{market_str}"
    user_prompt = build_user_prompt(enriched_text, ticker)
    messages = history + [{"role": "user", "content": user_prompt}]
    return call_groq(system_prompt, messages)

# ── Path B: No ticker — single-call analysis (original behavior) ───────────
logger.info("run_analysis | no ticker | single-call mode")
system_prompt = get_system_prompt(lang)
user_prompt = build_user_prompt(user_text)
messages = history + [{"role": "user", "content": user_prompt}]
return call_groq(system_prompt, messages)
```
