import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv(“TELEGRAM_BOT_TOKEN”)
GROQ_API_KEY = os.getenv(“GROQ_API_KEY”)

# ─── Groq Settings ────────────────────────────────────────────────────────────

GROQ_MODEL = “llama-3.3-70b-versatile”
GROQ_MAX_TOKENS = 700       # Increased from 600 — synthesis output needs room
GROQ_TEMPERATURE = 0.3

# ─── Session Settings ─────────────────────────────────────────────────────────

SESSION_TIMEOUT_SECONDS = 1800   # 30 minutes
MAX_HISTORY_MESSAGES = 4         # 2 pairs user+assistant

# ─── Feature Flags ────────────────────────────────────────────────────────────

# Set ATLAS_DEBATE_MODE=false in .env to disable 2-step debate (single-call fallback)

DEBATE_MODE = os.getenv(“ATLAS_DEBATE_MODE”, “true”).lower() == “true”

# Set ATLAS_MARKET_DATA=false in .env to disable yfinance fetching

MARKET_DATA_ENABLED = os.getenv(“ATLAS_MARKET_DATA”, “true”).lower() == “true”

# ─── Validation ───────────────────────────────────────────────────────────────

assert TELEGRAM_BOT_TOKEN, “TELEGRAM_BOT_TOKEN is not set in .env”
assert GROQ_API_KEY, “GROQ_API_KEY is not set in .env”
