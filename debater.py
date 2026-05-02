"""ATLAS Debater — Bull/Bear debate then synthesis."""

import logging
from groq_client import call_groq

logger = logging.getLogger(__name__)

_DEBATE_SYSTEM = """You are an internal multi-perspective analysis engine.
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
"""

_SYNTHESIS_ID = """Kamu adalah ATLAS, AI Market Co-Pilot.
Kamu menerima data market aktual dan hasil debat Bull vs Bear dari engine analisa internal.
Tugasmu: sintesis kedua perspektif menjadi satu analisa ATLAS yang terstruktur dan objektif.

ATURAN WAJIB:
1. Gunakan data market sebagai basis.
2. Bias KUAT hanya jika >= 3 faktor data mendukung.
3. Skenario alternatif wajib punya kondisi invalidasi spesifik.
4. Risiko dari BEAR case.
5. DILARANG: pasti, dijamin, beli sekarang, jual sekarang, 100%.
6. Maksimal 4 poin per section.

FORMAT:
[TICKER] — Analisa Multi-Perspektif
Bias: [BULLISH/BEARISH/NEUTRAL/INSUFFICIENT DATA] ([high/moderate/low] confidence)
Alasan:
• [poin berbasis data]
Skenario Alternatif:
• Jika [kondisi] -> [implikasi] | Batal jika: [invalidasi]
Risiko:
• [risiko dari bear case]
Kekuatan Data: [STRONG/MODERATE/WEAK/INSUFFICIENT]
Analisa konteks saja. Bukan rekomendasi transaksi.
"""

_SYNTHESIS_EN = """You are ATLAS, an AI Market Co-Pilot.
You receive real market data and a Bull vs Bear debate from your internal analysis engine.
Your task: synthesize both perspectives into one structured, objective ATLAS analysis.

MANDATORY RULES:
1. Use provided market data as primary basis.
2. Only state strong bias if >= 3 data factors support it.
3. Alternative scenario must include specific invalidation condition.
4. Risks must draw from BEAR case.
5. FORBIDDEN: guaranteed, definitely, buy now, sell now, 100%.
6. Max 4 bullet points per section.

FORMAT:
[TICKER] — Multi-Perspective Analysis
Bias: [BULLISH/BEARISH/NEUTRAL/INSUFFICIENT DATA] ([high/moderate/low] confidence)
Reasoning:
• [data-based point]
Alternative Scenario:
• If [condition] -> [implication] | Invalidated if: [condition]
Risks:
• [risk from bear case]
Data Strength: [STRONG/MODERATE/WEAK/INSUFFICIENT]
Analysis only. Not financial advice.
"""


def run_debate(ticker: str, market_data_str: str, user_text: str, history: list, lang: str, memory_context: str = "") -> str | None:
    debate_input = f"Asset: {ticker.upper()}\nUser question: {user_text}\n\n{market_data_str}"
    logger.info(f"[Debater] Step 1 — Bull/Bear | ticker={ticker}")
    bull_bear = call_groq(system_prompt=_DEBATE_SYSTEM, messages=[{"role": "user", "content": debate_input}])
    if not bull_bear or len(bull_bear) < 40 or "BULL:" not in bull_bear:
        logger.warning(f"[Debater] Step 1 failed for {ticker}")
        return None
    logger.info(f"[Debater] Step 1 OK | len={len(bull_bear)}")
    synthesis_system = _SYNTHESIS_EN if lang == "en" else _SYNTHESIS_ID
    synthesis_input = f"{market_data_str}\n\nDEBATE RESULT:\n{bull_bear}"
    if memory_context:
        synthesis_input += f"\n\n[Past context: {memory_context}]"
    synthesis_input += f"\n\nUser question: {user_text}"
    messages = history + [{"role": "user", "content": synthesis_input}]
    logger.info(f"[Debater] Step 2 — Synthesis | history_len={len(history)}")
    final = call_groq(system_prompt=synthesis_system, messages=messages)
    if not final or len(final) < 50:
        logger.warning(f"[Debater] Step 2 failed for {ticker}")
        return None
    logger.info(f"[Debater] Step 2 OK | len={len(final)}")
    return final
