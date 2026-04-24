import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_MAX_TOKENS = 600
GROQ_TEMPERATURE = 0.3

SESSION_TIMEOUT_SECONDS = 1800  # 30 minutes
MAX_HISTORY_MESSAGES = 4        # 2 pairs user+assistant

# Validate on import — fail fast if keys missing
assert TELEGRAM_BOT_TOKEN, "TELEGRAM_BOT_TOKEN is not set in .env"
assert GROQ_API_KEY, "GROQ_API_KEY is not set in .env"
