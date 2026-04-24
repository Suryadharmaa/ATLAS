“””
ATLAS Debater — adapted from TradingAgents:

- bull_researcher.py  → BULL perspective
- bear_researcher.py  → BEAR perspective
- aggressive/conservative/neutral debators → RISK synthesis

Architecture: 2 sequential Groq calls (not full multi-agent to stay lightweight):
Step 1 → Generate BULL case + BEAR case using real market data
Step 2 → Synthesize both into final structured ATLAS output

This replaces single-call analysis in analyzer.py for ticker-specific requests.
“””

import logging
from groq_client import call_groq

logger = logging.getLogger(**name**)

# ─── Step 1: Bull vs Bear ────────────────────────────────────────────────────

# Adapted from TradingAgents bull_researcher + bear_researcher prompts.

# Stripped of LangChain dependency — runs as a plain Groq call.

_DEBATE_SYSTEM = “”“You are an internal multi-perspective analysis engine.
Given market data and a ticker, generate exactly two short arguments:

BULL CASE: Why this asset has upside potential. Be specific, cite the data.
BEAR CASE: Why this asset is at risk or weak. Be specific, cite the data.

Rules:

- Max 3 bullet points per case.
- Each bullet must reference at least one data point (RSI, MACD, SMA, price change, etc.)
- No preamble. No conclusion. No formatting beyond the template below.
- Output STRICTLY in this format:

BULL:
• [point with data reference]
• [point with data reference]

BEAR:
• [point with data reference]
• [point with data reference]
“””

# ─── Step 2: Synthesis Prompts ───────────────────────────────────────────────

# Adapted from TradingAgents risk_mgmt debators → merged into one synthesis call

# to stay within ATLAS’s single-LLM architecture.

_SYNTHESIS_ID = “”“Kamu adalah ATLAS, AI Market Co-Pilot.

Kamu menerima data market aktual dan hasil debat Bull vs Bear dari engine analisa internal.
Tugasmu: sintesis kedua perspektif menjadi satu analisa ATLAS yang terstruktur dan objektif.

ATURAN WAJIB:

1. Gunakan data market yang diberikan sebagai basis — bukan opini umum.
1. Bias dinyatakan KUAT hanya jika ≥ 3 faktor data mendukung.
1. Skenario alternatif wajib memiliki kondisi invalidasi spesifik.
1. Risiko harus bersumber dari BEAR case yang diterima.
1. DILARANG: pasti, dijamin, beli sekarang, jual sekarang, 100%.
1. Maksimal 4 poin per section.

FORMAT OUTPUT WAJIB:
📊 [TICKER] — Analisa Multi-Perspektif

🎯 Bias: [BULLISH/BEARISH/NEUTRAL/INSUFFICIENT DATA] ([high/moderate/low] confidence)

📌 Alasan:
• [poin berbasis data]
• [poin berbasis data]

🔀 Skenario Alternatif:
• Jika [kondisi spesifik] → [implikasi] | Batal jika: [kondisi invalidasi]

📉 Risiko:
• [risiko dari bear case]
• [risiko dari bear case]

📶 Kekuatan Data: [STRONG/MODERATE/WEAK/INSUFFICIENT]

⚠️ Analisa konteks saja. Bukan rekomendasi transaksi.
“””

_SYNTHESIS_EN = “”“You are ATLAS, an AI Market Co-Pilot.

You receive real market data and a Bull vs Bear debate from your internal analysis engine.
Your task: synthesize both perspectives into one structured, objective ATLAS analysis.

MANDATORY RULES:

1. Use the provided market data as your primary basis — not general opinions.
1. Only state strong bias if ≥ 3 data factors support it.
1. Alternative scenario must include a specific invalidation condition.
1. Risks must draw from the BEAR case received.
1. FORBIDDEN: guaranteed, definitely, buy now, sell now, 100%.
1. Max 4 bullet points per section.

MANDATORY OUTPUT FORMAT:
📊 [TICKER] — Multi-Perspective Analysis

🎯 Bias: [BULLISH/BEARISH/NEUTRAL/INSUFFICIENT DATA] ([high/moderate/low] confidence)

📌 Reasoning:
• [data-based point]
• [data-based point]

🔀 Alternative Scenario:
• If [specific condition] → [implication] | Invalidated if: [specific condition]

📉 Risks:
• [risk from bear case]
• [risk from bear case]

📶 Data Strength: [STRONG/MODERATE/WEAK/INSUFFICIENT]

⚠️ Analysis only. Not financial advice.
“””

def run_debate(
ticker: str,
market_data_str: str,
user_text: str,
history: list,
lang: str,
memory_context: str = “”,
) -> str | None:
“””
Execute 2-step debate analysis.

```
Step 1: Generate Bull + Bear cases (new Groq call, no history — focused task)
Step 2: Synthesize into final ATLAS output (includes session history)

Returns final ATLAS-formatted string, or None if Step 1 fails (fallback to single-call).
"""

# ── Step 1: Bull vs Bear ──────────────────────────────────────────────────
debate_input = (
    f"Asset: {ticker.upper()}\n"
    f"User question: {user_text}\n\n"
    f"{market_data_str}"
)

logger.info(f"[Debater] Step 1 — Bull/Bear | ticker={ticker}")
bull_bear = call_groq(
    system_prompt=_DEBATE_SYSTEM,
    messages=[{"role": "user", "content": debate_input}],
)

if not bull_bear or len(bull_bear) < 40 or "BULL:" not in bull_bear:
    logger.warning(f"[Debater] Step 1 failed or malformed for {ticker} — falling back")
    return None

logger.info(f"[Debater] Step 1 OK | len={len(bull_bear)}")

# ── Step 2: Synthesis ─────────────────────────────────────────────────────
synthesis_system = _SYNTHESIS_EN if lang == "en" else _SYNTHESIS_ID

synthesis_input = (
    f"{market_data_str}\n\n"
    f"━━ INTERNAL DEBATE RESULT ━━\n"
    f"{bull_bear}\n"
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
)

if memory_context:
    synthesis_input += f"\n\n[Past context for this user: {memory_context}]"

synthesis_input += f"\n\nUser question: {user_text}"

# Include session history for conversation continuity
messages = history + [{"role": "user", "content": synthesis_input}]

logger.info(f"[Debater] Step 2 — Synthesis | history_len={len(history)}")
final = call_groq(system_prompt=synthesis_system, messages=messages)

if not final or len(final) < 50:
    logger.warning(f"[Debater] Step 2 failed for {ticker}")
    return None

logger.info(f"[Debater] Step 2 OK | len={len(final)}")
return final
```
