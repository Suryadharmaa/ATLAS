"""ATLAS Market Memory — BM25 recall for session context enrichment."""

import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank_bm25 not installed — memory system disabled.")


class MarketMemory:
    """Per-session memory using BM25 scoring."""

    def __init__(self):
        self.situations: List[str] = []
        self.summaries: List[str] = []
        self._bm25: Optional["BM25Okapi"] = None

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\b\w+\b", text.lower())

    def _rebuild(self):
        if self.situations and BM25_AVAILABLE:
            self._bm25 = BM25Okapi([self._tokenize(s) for s in self.situations])
        else:
            self._bm25 = None

    def add(self, situation: str, summary: str):
        self.situations.append(situation)
        self.summaries.append(summary[:400])
        self._rebuild()

    def recall(self, current_situation: str, n: int = 1) -> List[dict]:
        if not self.situations or not self._bm25:
            return []
        tokens = self._tokenize(current_situation)
        scores = self._bm25.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n]
        # With small corpora BM25 can give negative scores — still return top match
        if len(self.situations) <= 3:
            return [
                {"situation": self.situations[i], "summary": self.summaries[i], "score": round(float(scores[i]), 3)}
                for i in top_indices
            ]
        return [
            {"situation": self.situations[i], "summary": self.summaries[i], "score": round(float(scores[i]), 3)}
            for i in top_indices if scores[i] > 0
        ]

    def clear(self):
        self.situations = []
        self.summaries = []
        self._bm25 = None

    def __len__(self):
        return len(self.situations)
