“””
ATLAS Market Data — adapted from TradingAgents dataflows/y_finance.py + stockstats_utils.py
Fetches real OHLCV data via yfinance and computes key technical indicators.
Falls back gracefully if yfinance is unavailable or ticker not found.
“””

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(**name**)

try:
import yfinance as yf
import pandas as pd
YFINANCE_AVAILABLE = True
except ImportError:
YFINANCE_AVAILABLE = False
logger.warning(“yfinance/pandas not installed. Market data disabled.”)

# ─── Ticker Mapping ──────────────────────────────────────────────────────────

# Maps ATLAS tickers → yfinance symbols

YFINANCE_MAP = {
# Crypto
“BTC”: “BTC-USD”,
“ETH”: “ETH-USD”,
“SOL”: “SOL-USD”,
“BNB”: “BNB-USD”,
“XRP”: “XRP-USD”,
“MATIC”: “MATIC-USD”,
“DOGE”: “DOGE-USD”,
# Forex & Metals
“XAUUSD”: “GC=F”,       # Gold futures
“EURUSD”: “EURUSD=X”,
“DXY”: “DX-Y.NYB”,      # US Dollar Index
# IDX Stocks
“BBCA”: “BBCA.JK”,
“BBRI”: “BBRI.JK”,
“TLKM”: “TLKM.JK”,
“GOTO”: “GOTO.JK”,
“BMRI”: “BMRI.JK”,
“ASII”: “ASII.JK”,
# US Stocks (pass-through)
“AAPL”: “AAPL”,
“NVDA”: “NVDA”,
“TSLA”: “TSLA”,
“META”: “META”,
“MSFT”: “MSFT”,
}

# ─── Indicator Computations ───────────────────────────────────────────────────

def _rsi(close: “pd.Series”, period: int = 14) -> Optional[float]:
“”“RSI — adapted from TradingAgents stockstats_utils pattern.”””
if len(close) < period + 1:
return None
delta = close.diff()
gain = delta.clip(lower=0).rolling(period).mean()
loss = (-delta.clip(upper=0)).rolling(period).mean()
rs = gain / loss.replace(0, float(“nan”))
rsi = 100 - (100 / (1 + rs))
val = rsi.iloc[-1]
return round(float(val), 2) if not pd.isna(val) else None

def _macd(close: “pd.Series”):
“”“MACD line + signal line.”””
ema12 = close.ewm(span=12, adjust=False).mean()
ema26 = close.ewm(span=26, adjust=False).mean()
macd = ema12 - ema26
signal = macd.ewm(span=9, adjust=False).mean()
return (
round(float(macd.iloc[-1]), 4),
round(float(signal.iloc[-1]), 4),
)

def _atr(high: “pd.Series”, low: “pd.Series”, close: “pd.Series”, period: int = 14) -> Optional[float]:
“”“Average True Range.”””
prev_close = close.shift(1)
tr = pd.concat([
(high - low).abs(),
(high - prev_close).abs(),
(low - prev_close).abs(),
], axis=1).max(axis=1)
val = tr.rolling(period).mean().iloc[-1]
return round(float(val), 4) if not pd.isna(val) else None

# ─── Main Fetch Function ──────────────────────────────────────────────────────

def fetch_market_snapshot(ticker: str) -> Optional[dict]:
“””
Fetch last 60 days OHLCV + compute: RSI, MACD, SMA20, SMA50, ATR, Volume ratio.
Returns dict or None on failure (silent — analysis continues without data).
“””
if not YFINANCE_AVAILABLE:
return None

```
yf_symbol = YFINANCE_MAP.get(ticker.upper(), ticker.upper())

try:
    end = datetime.now()
    start = end - timedelta(days=75)  # Extra buffer for indicator warmup

    ticker_obj = yf.Ticker(yf_symbol)
    df = ticker_obj.history(
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        auto_adjust=True,
    )

    if df.empty or len(df) < 20:
        logger.warning(f"Insufficient market data for {ticker} ({yf_symbol})")
        return None

    # Remove timezone for clean computation
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    close = df["Close"].dropna()
    high = df["High"].dropna()
    low = df["Low"].dropna()
    volume = df["Volume"].dropna()

    current_price = round(float(close.iloc[-1]), 6)

    # 7-day price change
    idx_7d = -8 if len(close) >= 8 else 0
    price_7d = float(close.iloc[idx_7d])
    change_7d = round(((current_price - price_7d) / price_7d) * 100, 2)

    # SMAs
    sma20 = round(float(close.rolling(20).mean().iloc[-1]), 6)
    sma50_series = close.rolling(50).mean()
    sma50 = round(float(sma50_series.iloc[-1]), 6) if len(close) >= 50 and not pd.isna(sma50_series.iloc[-1]) else None

    # Momentum
    rsi = _rsi(close)
    macd_val, macd_signal = _macd(close)

    # Volatility
    atr = _atr(high, low, close)

    # Volume trend
    avg_vol = float(volume.rolling(20).mean().iloc[-1])
    last_vol = float(volume.iloc[-1])
    vol_ratio = round(last_vol / avg_vol, 2) if avg_vol > 0 else None

    return {
        "ticker": ticker.upper(),
        "yf_symbol": yf_symbol,
        "price": current_price,
        "change_7d_pct": change_7d,
        "sma20": sma20,
        "sma50": sma50,
        "rsi": rsi,
        "macd": macd_val,
        "macd_signal": macd_signal,
        "atr": atr,
        "volume_ratio": vol_ratio,
        "data_points": len(df),
    }

except Exception as e:
    logger.error(f"market_data fetch error [{ticker}→{yf_symbol}]: {e}")
    return None
```

def format_snapshot_for_prompt(snapshot: Optional[dict]) -> str:
“””
Convert market snapshot → readable string for LLM context.
Adapted from TradingAgents get_stock_stats_indicators_window pattern.
“””
if not snapshot:
return “[MARKET DATA: Unavailable — analysis based on LLM knowledge only]”

```
rsi = snapshot.get("rsi")
rsi_label = (
    "⚠️ Overbought (>70)" if rsi and rsi > 70
    else ("⚠️ Oversold (<30)" if rsi and rsi < 30 else "Neutral (30–70)")
)

macd = snapshot.get("macd")
sig = snapshot.get("macd_signal")
macd_label = "Bullish (MACD > Signal)" if (macd and sig and macd > sig) else "Bearish (MACD < Signal)"

price = snapshot["price"]
sma20 = snapshot["sma20"]
sma50 = snapshot.get("sma50")
change = snapshot.get("change_7d_pct", 0)
direction = "▲" if change >= 0 else "▼"

vol = snapshot.get("volume_ratio")
vol_label = f"{vol}x avg ({'above' if vol and vol > 1 else 'below'} average)" if vol else "N/A"

lines = [
    f"━━ MARKET DATA: {snapshot['ticker']} ━━",
    f"Price     : {price} {direction} {change}% (7d)",
    f"SMA20     : {sma20} → {'Price ABOVE SMA20 ✓' if price > sma20 else 'Price BELOW SMA20 ✗'}",
    f"SMA50     : {sma50} → {'Price ABOVE SMA50 ✓' if sma50 and price > sma50 else 'Price BELOW SMA50 ✗'}" if sma50 else "SMA50     : N/A (< 50 data points)",
    f"RSI(14)   : {rsi} → {rsi_label}" if rsi else "RSI(14)   : N/A",
    f"MACD      : {macd} | Signal: {sig} → {macd_label}" if macd and sig else "MACD      : N/A",
    f"ATR(14)   : {snapshot.get('atr', 'N/A')} (volatility measure)",
    f"Volume    : {vol_label}",
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━",
]
return "\n".join(lines)
```
