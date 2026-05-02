"""ATLAS Test Suite — Comprehensive validation."""

import os
import sys
import time
import importlib.util
import pytest
from unittest.mock import patch, MagicMock

os.environ["TELEGRAM_BOT_TOKEN"] = "test_token_123"
os.environ["GROQ_API_KEY"] = "test_key_456"


class TestConfig:
    def test_config_loads(self):
        import config
        assert config.TELEGRAM_BOT_TOKEN == "test_token_123"
        assert config.GROQ_API_KEY == "test_key_456"

    def test_groq_settings(self):
        import config
        assert config.GROQ_MODEL == "llama-3.3-70b-versatile"
        assert config.GROQ_MAX_TOKENS == 1024
        assert config.GROQ_TEMPERATURE == 0.3

    def test_session_settings(self):
        import config
        assert config.SESSION_TIMEOUT_SECONDS == 1800
        assert config.MAX_HISTORY_MESSAGES == 4

    def test_feature_flags(self):
        import config
        assert isinstance(config.DEBATE_MODE, bool)
        assert isinstance(config.MARKET_DATA_ENABLED, bool)


class TestPrompts:
    def test_get_system_prompt_id(self):
        from prompts import get_system_prompt
        prompt = get_system_prompt("id")
        assert "ATLAS" in prompt

    def test_get_system_prompt_en(self):
        from prompts import get_system_prompt
        prompt = get_system_prompt("en")
        assert "ATLAS" in prompt

    def test_build_user_prompt_with_ticker(self):
        from prompts import build_user_prompt
        result = build_user_prompt("analyze BTC", "BTC")
        assert "[TICKER: BTC]" in result

    def test_build_user_prompt_without_ticker(self):
        from prompts import build_user_prompt
        result = build_user_prompt("what is the market doing?")
        assert result == "what is the market doing?"

    def test_detect_lang_indonesian(self):
        from prompts import detect_lang
        assert detect_lang("analisa BTC hari ini") == "id"

    def test_detect_lang_english(self):
        from prompts import detect_lang
        assert detect_lang("what is the risk on BTC?") == "en"

    def test_out_of_scope_messages_exist(self):
        from prompts import OUT_OF_SCOPE_ID, OUT_OF_SCOPE_EN
        assert len(OUT_OF_SCOPE_ID) > 20
        assert len(OUT_OF_SCOPE_EN) > 20


class TestFormatter:
    def test_post_process_valid_text(self):
        from formatter import post_process
        text = "This is a valid analysis with enough content to pass checks."
        result = post_process(text, "en")
        assert len(result) > 0

    def test_post_process_empty_returns_fallback(self):
        from formatter import post_process
        result = post_process("", "en")
        assert "ATLAS" in result

    def test_post_process_none_returns_fallback(self):
        from formatter import post_process
        result = post_process(None, "id")
        assert "ATLAS" in result

    def test_post_process_removes_forbidden_words(self):
        from formatter import post_process
        text = "This stock will definitely go up. Guaranteed profit."
        result = post_process(text, "en")
        assert "[removed]" in result

    def test_post_process_removes_indonesian_forbidden(self):
        from formatter import post_process
        text = "Pasti naik, dijamin untung besar."
        result = post_process(text, "id")
        assert "[dihapus]" in result

    def test_post_process_truncates_long_text(self):
        from formatter import post_process, MAX_OUTPUT_LENGTH
        text = "x" * 2000
        result = post_process(text, "en")
        assert len(result) <= MAX_OUTPUT_LENGTH + 50

    def test_post_process_adds_disclaimer_id(self):
        from formatter import post_process, DISCLAIMER_ID
        text = "Some analysis content that is long enough to be valid here."
        result = post_process(text, "id")
        assert DISCLAIMER_ID in result

    def test_post_process_adds_disclaimer_en(self):
        from formatter import post_process, DISCLAIMER_EN
        text = "Some analysis content that is long enough to be valid here."
        result = post_process(text, "en")
        assert DISCLAIMER_EN in result

    def test_safe_to_send_valid(self):
        from formatter import safe_to_send
        text = "This is a valid market analysis with enough content.\n\nAnalysis only. Not financial advice."
        assert safe_to_send(text) is True

    def test_safe_to_send_empty(self):
        from formatter import safe_to_send
        assert safe_to_send("") is False
        assert safe_to_send(None) is False

    def test_safe_to_send_too_short(self):
        from formatter import safe_to_send
        assert safe_to_send("short") is False

    def test_safe_to_send_no_disclaimer(self):
        from formatter import safe_to_send
        text = "This is a long enough text but has no disclaimer at all " * 3
        assert safe_to_send(text) is False

    def test_safe_to_send_indonesian_disclaimer(self):
        from formatter import safe_to_send
        text = "Analisa valid.\n\nAnalisa konteks saja. Bukan rekomendasi transaksi."
        assert safe_to_send(text) is True


class TestSession:
    def setup_method(self):
        import session
        session._sessions.clear()

    def test_get_session_creates_new(self):
        from session import get_session
        s = get_session(12345)
        assert s["lang"] == "id"
        assert s["warned"] is False
        assert s["history"] == []

    def test_get_session_returns_same(self):
        from session import get_session
        s1 = get_session(12345)
        s2 = get_session(12345)
        assert s1 is s2

    def test_reset_session(self):
        from session import get_session, reset_session, add_to_history
        add_to_history(12345, "user", "test")
        reset_session(12345)
        s = get_session(12345)
        assert len(s["history"]) == 0

    def test_add_to_history(self):
        from session import add_to_history, get_session
        add_to_history(12345, "user", "hello")
        add_to_history(12345, "assistant", "hi")
        s = get_session(12345)
        assert len(s["history"]) == 2

    def test_history_max_limit(self):
        from session import add_to_history, get_session
        from config import MAX_HISTORY_MESSAGES
        for i in range(10):
            add_to_history(12345, "user", f"msg {i}")
        s = get_session(12345)
        assert len(s["history"]) == MAX_HISTORY_MESSAGES

    def test_set_lang(self):
        from session import get_session, set_lang
        set_lang(12345, "en")
        assert get_session(12345)["lang"] == "en"

    def test_set_warned(self):
        from session import get_session, set_warned
        set_warned(12345)
        assert get_session(12345)["warned"] is True

    def test_session_timeout(self):
        from session import get_session, add_to_history
        add_to_history(12345, "user", "test")
        s = get_session(12345)
        s["last_active"] = time.time() - 2000
        s2 = get_session(12345)
        assert len(s2["history"]) == 0

    def test_multiple_chat_sessions(self):
        from session import get_session, set_lang
        set_lang(111, "en")
        set_lang(222, "id")
        assert get_session(111)["lang"] == "en"
        assert get_session(222)["lang"] == "id"

    def test_memory_instance_created(self):
        from session import get_session
        s = get_session(12345)
        assert "memory" in s


class TestMemory:
    def test_memory_init(self):
        from memory import MarketMemory
        m = MarketMemory()
        assert len(m) == 0

    def test_memory_add(self):
        from memory import MarketMemory
        m = MarketMemory()
        m.add("BTC RSI:62 MACD:bullish", "Bullish analysis")
        assert len(m) == 1

    def test_memory_recall(self):
        from memory import MarketMemory, BM25_AVAILABLE
        if not BM25_AVAILABLE:
            pytest.skip("rank_bm25 not installed")
        m = MarketMemory()
        m.add("BTC RSI:62 MACD:bullish change7d:+3.2%", "Bullish BTC analysis")
        m.add("ETH RSI:45 MACD:bearish change7d:-1.5%", "Bearish ETH analysis")
        results = m.recall("BTC RSI:60 MACD:bullish change7d:+3.0%", n=1)
        assert len(results) > 0
        assert "BTC" in results[0]["situation"]

    def test_memory_recall_empty(self):
        from memory import MarketMemory
        m = MarketMemory()
        assert m.recall("BTC anything") == []

    def test_memory_clear(self):
        from memory import MarketMemory
        m = MarketMemory()
        m.add("test", "summary")
        m.clear()
        assert len(m) == 0

    def test_memory_summary_truncated(self):
        from memory import MarketMemory
        m = MarketMemory()
        m.add("test", "x" * 1000)
        assert len(m.summaries[0]) <= 400


class TestAnalyzer:
    def test_extract_ticker_btc(self):
        from analyzer import extract_ticker
        assert extract_ticker("analyze BTC") == "BTC"
        assert extract_ticker("analisa btc hari ini") == "BTC"

    def test_extract_ticker_eth(self):
        from analyzer import extract_ticker
        assert extract_ticker("what about ETH?") == "ETH"

    def test_extract_ticker_unknown(self):
        from analyzer import extract_ticker
        assert extract_ticker("what is happening?") is None

    def test_extract_ticker_with_punctuation(self):
        from analyzer import extract_ticker
        assert extract_ticker("BTC!") == "BTC"

    def test_is_out_of_scope_buy(self):
        from analyzer import is_out_of_scope
        assert is_out_of_scope("beli BTC sekarang") is True
        assert is_out_of_scope("buy ETH now") is True

    def test_is_out_of_scope_sell(self):
        from analyzer import is_out_of_scope
        assert is_out_of_scope("jual BTC") is True
        assert is_out_of_scope("sell ETH") is True

    def test_is_out_of_scope_valid(self):
        from analyzer import is_out_of_scope
        assert is_out_of_scope("analyze BTC") is False
        assert is_out_of_scope("analisa BBCA hari ini") is False

    def test_known_tickers_coverage(self):
        from analyzer import KNOWN_TICKERS
        assert "BTC" in KNOWN_TICKERS
        assert "BBCA" in KNOWN_TICKERS
        assert "XAUUSD" in KNOWN_TICKERS

    @patch("analyzer.call_groq")
    @patch("analyzer.run_debate", return_value=None)
    @patch("analyzer.fetch_market_snapshot", return_value=None)
    def test_run_analysis_no_ticker_fallback(self, mock_fetch, mock_debate, mock_groq):
        from analyzer import run_analysis
        mock_groq.return_value = "Analysis result with enough content to be valid."
        result = run_analysis("what is happening?", [], "id")
        assert result is not None

    def test_run_analysis_out_of_scope_returns_none(self):
        from analyzer import run_analysis
        result = run_analysis("beli BTC sekarang", [], "id")
        assert result is None


class TestMarketData:
    def test_format_snapshot_valid(self):
        from market_data import format_snapshot_for_prompt
        snapshot = {
            "ticker": "BTC", "price": 50000.0, "change_7d_pct": 3.5,
            "sma20": 49000.0, "sma50": 48000.0, "rsi": 62.5,
            "macd": 100.0, "macd_signal": 80.0, "atr": 1500.0, "volume_ratio": 1.2,
        }
        result = format_snapshot_for_prompt(snapshot)
        assert "BTC" in result
        assert "50000" in result

    def test_format_snapshot_none(self):
        from market_data import format_snapshot_for_prompt
        result = format_snapshot_for_prompt(None)
        assert "Unavailable" in result

    def test_ticker_mapping(self):
        from market_data import YFINANCE_MAP
        assert YFINANCE_MAP["BTC"] == "BTC-USD"
        assert YFINANCE_MAP["XAUUSD"] == "GC=F"
        assert YFINANCE_MAP["BBCA"] == "BBCA.JK"


class TestDebater:
    @patch("debater.call_groq")
    def test_run_debate_success(self, mock_groq):
        from debater import run_debate
        mock_groq.side_effect = [
            "BULL:\n• Strong RSI at 62\n• MACD bullish\n\nBEAR:\n• High volatility",
            "BTC Analysis. Bias: BULLISH. Analysis only. Not financial advice.",
        ]
        result = run_debate("BTC", "Price: 50000", "analyze BTC", [], "en")
        assert result is not None
        assert mock_groq.call_count == 2

    @patch("debater.call_groq")
    def test_run_debate_step1_fails(self, mock_groq):
        from debater import run_debate
        mock_groq.return_value = None
        result = run_debate("BTC", "Price: 50000", "analyze BTC", [], "en")
        assert result is None

    @patch("debater.call_groq")
    def test_run_debate_step1_malformed(self, mock_groq):
        from debater import run_debate
        mock_groq.return_value = "Not valid format"
        result = run_debate("BTC", "Price: 50000", "analyze BTC", [], "en")
        assert result is None


class TestBot:
    def test_all_modules_importable(self):
        modules = ["config", "prompts", "formatter", "session", "memory", "market_data", "analyzer", "debater", "groq_client"]
        for mod_name in modules:
            spec = importlib.util.find_spec(mod_name)
            assert spec is not None, f"Module {mod_name} not found"


class TestIntegration:
    def setup_method(self):
        import session
        session._sessions.clear()

    def test_full_flow_no_ticker(self):
        from analyzer import is_out_of_scope, extract_ticker
        from prompts import detect_lang
        text = "what is the market doing?"
        assert detect_lang(text) == "en"
        assert is_out_of_scope(text) is False
        assert extract_ticker(text) is None

    def test_full_flow_with_ticker(self):
        from analyzer import is_out_of_scope, extract_ticker
        from prompts import get_system_prompt, build_user_prompt
        text = "analyze BTC"
        assert is_out_of_scope(text) is False
        ticker = extract_ticker(text)
        assert ticker == "BTC"
        system = get_system_prompt("en")
        user = build_user_prompt(text, ticker)
        assert "[TICKER: BTC]" in user

    def test_out_of_scope_blocked(self):
        from analyzer import is_out_of_scope
        assert is_out_of_scope("beli BTC sekarang") is True
        assert is_out_of_scope("jual ETH") is True

    def test_formatter_safety_pipeline(self):
        from formatter import post_process, safe_to_send
        raw = "BTC is guaranteed to go up. Buy now. " * 10
        processed = post_process(raw, "en")
        assert "Not financial advice" in processed or "Analysis only" in processed


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
