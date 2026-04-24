“””
ATLAS Bot — updated to pass session memory to run_analysis.
All other logic unchanged from v1.
“””

import logging
from telegram import Update
from telegram.ext import (
ApplicationBuilder,
CommandHandler,
MessageHandler,
filters,
ContextTypes,
)
from config import TELEGRAM_BOT_TOKEN
from session import (
get_session, reset_session, add_to_history,
set_lang, set_warned, update_last_active,
)
from prompts import (
OUT_OF_SCOPE_ID, OUT_OF_SCOPE_EN,
RISK_WARNING_ID, RISK_WARNING_EN,
detect_lang,
)
from analyzer import run_analysis, is_out_of_scope, extract_ticker
from formatter import post_process, safe_to_send

logging.basicConfig(
format=”%(asctime)s [%(levelname)s] %(name)s: %(message)s”,
level=logging.INFO,
)
logger = logging.getLogger(**name**)

ONBOARDING_ID = (
“👋 Selamat datang di *ATLAS*.\n\n”
“Saya membantu kamu memahami kondisi market — “
“bukan memberi sinyal beli/jual.\n\n”
“Cara pakai:\n”
“• /analyze BTC — analisa langsung dengan data real-time\n”
“• Atau ketik: *"analisa BBCA"* atau *"risk on ETH"*\n\n”
“⚠️ Semua output bersifat edukatif. Bukan rekomendasi investasi.”
)

ONBOARDING_EN = (
“👋 Welcome to *ATLAS*.\n\n”
“I help you understand market conditions — “
“not give buy/sell signals.\n\n”
“How to use:\n”
“• /analyze BTC — direct analysis with real-time data\n”
“• Or type: *"analyze BBCA"* or *"risk on ETH"*\n\n”
“⚠️ All output is educational. Not investment advice.”
)

HELP_ID = (
“*ATLAS — Bantuan*\n\n”
“• /analyze [ticker] — analisa market (data real-time + multi-perspektif)\n”
“• /disclaimer — tampilkan disclaimer lengkap\n”
“• /start — reset sesi\n\n”
“Contoh: /analyze BTC, /analyze BBCA, /analyze XAUUSD”
)

HELP_EN = (
“*ATLAS — Help*\n\n”
“• /analyze [ticker] — market analysis (real-time data + multi-perspective)\n”
“• /disclaimer — show full disclaimer\n”
“• /start — reset session\n\n”
“Examples: /analyze BTC, /analyze AAPL, /analyze EURUSD”
)

DISCLAIMER_FULL_ID = (
“⚠️ *Disclaimer ATLAS*\n\n”
“ATLAS adalah tools analisa konteks market berbasis AI.\n”
“Output ATLAS bukan merupakan rekomendasi investasi, “
“sinyal trading, atau saran finansial dalam bentuk apapun.\n\n”
“Semua keputusan investasi dan trading sepenuhnya “
“menjadi tanggung jawab pengguna.\n\n”
“ATLAS tidak bertanggung jawab atas kerugian apapun “
“yang timbul dari penggunaan informasi ini.”
)

# ─── Handlers ───────────────────────────────────────────────────────────────

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
chat_id = update.effective_chat.id
reset_session(chat_id)

```
lang = detect_lang(update.message.text or "")
set_lang(chat_id, lang)

text = ONBOARDING_EN if lang == "en" else ONBOARDING_ID
await update.message.reply_text(text, parse_mode="Markdown")
```

async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
chat_id = update.effective_chat.id
session = get_session(chat_id)
text = HELP_EN if session[“lang”] == “en” else HELP_ID
await update.message.reply_text(text, parse_mode=“Markdown”)

async def handle_disclaimer(update: Update, context: ContextTypes.DEFAULT_TYPE):
await update.message.reply_text(DISCLAIMER_FULL_ID, parse_mode=“Markdown”)

async def handle_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Handler for /analyze [ticker] command.”””
chat_id = update.effective_chat.id
session = get_session(chat_id)
update_last_active(chat_id)

```
args = context.args
if not args:
    msg = (
        "Gunakan format: /analyze [ticker]\nContoh: /analyze BTC"
        if session["lang"] == "id"
        else "Usage: /analyze [ticker]\nExample: /analyze BTC"
    )
    await update.message.reply_text(msg)
    return

ticker = args[0].upper()
user_text = f"Analyze {ticker}"
await _process_analysis(update, chat_id, session, user_text)
```

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Handler for free-text messages.”””
chat_id = update.effective_chat.id
text = update.message.text or “”

```
if not text.strip():
    return

session = get_session(chat_id)
update_last_active(chat_id)

# Auto-detect language
detected = detect_lang(text)
if detected != session["lang"]:
    set_lang(chat_id, detected)
    session["lang"] = detected

# Out of scope check
if is_out_of_scope(text):
    msg = OUT_OF_SCOPE_EN if session["lang"] == "en" else OUT_OF_SCOPE_ID
    await update.message.reply_text(msg)
    return

# Ticker required for free-text analysis
ticker = extract_ticker(text)
if not ticker:
    clarification = (
        "Kamu ingin analisa aset apa? Contoh: BTC, BBCA, ETH, XAUUSD.\n"
        "Atau gunakan: /analyze [ticker]"
        if session["lang"] == "id"
        else "Which asset do you want to analyze? Example: BTC, AAPL, ETH.\n"
        "Or use: /analyze [ticker]"
    )
    await update.message.reply_text(clarification)
    return

await _process_analysis(update, chat_id, session, text)
```

async def _process_analysis(
update: Update, chat_id: int, session: dict, user_text: str
):
“”“Shared logic: risk warning → analysis → send.”””
lang = session[“lang”]

```
# Send risk warning once per session
if not session["warned"]:
    warning = RISK_WARNING_EN if lang == "en" else RISK_WARNING_ID
    await update.message.reply_text(warning, parse_mode="Markdown")
    set_warned(chat_id)

# Show typing indicator
await update.message.chat.send_action("typing")

# Run analysis — pass memory instance from session
result = run_analysis(
    user_text=user_text,
    history=session["history"],
    lang=lang,
    memory=session.get("memory"),   # ← MarketMemory instance (or None)
)
result = post_process(result, lang)

# Final safety gate
if not safe_to_send(result):
    logger.error(f"safe_to_send blocked for chat_id={chat_id}")
    fallback = (
        "ATLAS tidak dapat memproses analisa saat ini. Silakan coba lagi."
        if lang == "id"
        else "ATLAS could not process this analysis. Please try again."
    )
    await update.message.reply_text(fallback)
    return

# Save to history
add_to_history(chat_id, "user", user_text)
add_to_history(chat_id, "assistant", result)

await update.message.reply_text(result)
```

# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

```
app.add_handler(CommandHandler("start", handle_start))
app.add_handler(CommandHandler("help", handle_help))
app.add_handler(CommandHandler("disclaimer", handle_disclaimer))
app.add_handler(CommandHandler("analyze", handle_analyze))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

logger.info("ATLAS v2 started — debate mode + market data + memory active.")
app.run_polling()
```

if **name** == “**main**”:
main()
