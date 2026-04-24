“””
ATLAS Market Memory — adapted from TradingAgents FinancialSituationMemory (memory.py).
Uses BM25 (offline, zero-cost) to retrieve past analysis contexts per user session.
On each new analysis, the closest past situation is injected as context to the LLM.
“””

import re
import logging
from typing import List, Optional

logger = logging.getLogger(**name**)

try:
from rank_bm25 import BM25Okapi
BM25_AVAILABLE = True
except ImportError:
BM25_AVAILABLE = False
logger.warning(“rank_bm25 not installed — memory system disabled. Run: pip install rank-bm25”)

class MarketMemory:
“””
Per-session memory for ATLAS.

```
Stores (market_situation_key, analysis_summary) pairs.
On recall(), uses BM25 to find the most similar past situation
and returns its summary as context for the next LLM call.

Lifecycle: one instance per Telegram session (lives in session dict).
"""

def __init__(self):
    self.situations: List[str] = []   # market context strings
    self.summaries: List[str] = []    # shortened past analysis outputs
    self._bm25: Optional["BM25Okapi"] = None

def _tokenize(self, text: str) -> List[str]:
    """Whitespace + punctuation tokenizer (same as TradingAgents)."""
    return re.findall(r"\b\w+\b", text.lower())

def _rebuild(self):
    if self.situations and BM25_AVAILABLE:
        self._bm25 = BM25Okapi([self._tokenize(s) for s in self.situations])
    else:
        self._bm25 = None

def add(self, situation: str, summary: str):
    """
    Store a market situation and the analysis generated for it.
    situation: compact key e.g. "BTC RSI:62 MACD:bullish change7d:+3.2%"
    summary:   first 400 chars of the ATLAS output for that situation
    """
    self.situations.append(situation)
    self.summaries.append(summary[:400])
    self._rebuild()
    logger.debug(f"Memory: stored situation #{len(self.situations)}")

def recall(self, current_situation: str, n: int = 1) -> List[dict]:
    """
    Return top-n most similar past situations using BM25 scoring.
    Returns empty list if no memory or BM25 unavailable.
    Only returns entries with score > 0 (actual match).
    """
    if not self.situations or not self._bm25:
        return []

    tokens = self._tokenize(current_situation)
    scores = self._bm25.get_scores(tokens)

    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True,
    )[:n]

    return [
        {
            "situation": self.situations[i],
            "summary": self.summaries[i],
            "score": round(float(scores[i]), 3),
        }
        for i in top_indices
        if scores[i] > 0
    ]

def clear(self):
    self.situations = []
    self.summaries = []
    self._bm25 = None

def __len__(self):
    return len(self.situations)
```
