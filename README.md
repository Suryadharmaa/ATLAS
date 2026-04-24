# ATLAS — AI Market Co-Pilot

ATLAS is a Telegram-based AI market analysis assistant for Forex, Crypto, Metals, and selected stocks. It is designed as a **co-pilot**, not a signal bot: the goal is to help users understand market context, think through risk, and make more disciplined decisions.

## What ATLAS does

- Accepts market questions from Telegram chat or commands
- Detects the user’s intent and language (ID/EN)
- Sends the request to Groq for fast AI reasoning
- Returns a structured analysis with:
  - Bias
  - Reasoning
  - Alternative scenario
  - Risks
  - Data strength
- Adds a disclaimer so the bot stays educational and risk-aware

## Core product principles

1. **Context over prediction**  
   ATLAS explains what is happening, not “guaranteed” market direction.

2. **Risk first**  
   Every answer should remind the user that market decisions carry risk.

3. **Simple MVP**  
   The first version is intentionally small so it can be tested quickly.

4. **Low-cost stack**  
   Built to work with free or low-budget tooling.

## Current stack

The prototype uses:

- `python-telegram-bot` for Telegram bot handling
- `openai` SDK for Groq-compatible chat completions
- `python-dotenv` for environment variables

## How the bot works

```text
User message in Telegram
→ bot.py receives the message
→ session.py stores language / history / warning state
→ analyzer.py detects ticker and builds prompts
→ groq_client.py calls Groq API
→ formatter.py cleans and validates the result
→ Telegram sends the final answer back to the user
```

## Project structure

```text
atlas-bot/
├── bot.py           # Telegram handlers and app entry point
├── analyzer.py      # Intent parsing and analysis workflow
├── groq_client.py   # Groq API client
├── prompts.py       # System prompt, user prompt, language helpers
├── formatter.py     # Output cleanup and safety checks
├── session.py       # In-memory chat session state
├── config.py        # Environment variables and constants
├── requirements.txt # Python dependencies
└── README.md        # Project documentation
```

## Commands

- `/start` — reset session and show onboarding
- `/help` — show bot usage
- `/disclaimer` — show the full disclaimer
- `/analyze [ticker]` — run a market analysis

### Example

```text
/analyze BTC
/analyze XAUUSD
/analyze BBCA
```

You can also send free text such as:

```text
analisa XAUUSD hari ini
analyze BTC
what is the bias on ETH?
```

## Environment variables

Create a `.env` file with:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key
```

## Install

```bash
pip install -r requirements.txt
```

## Run locally

```bash
python bot.py
```

## Telegram setup

1. Open **@BotFather** in Telegram
2. Create a new bot
3. Copy the bot token into `.env`
4. If testing in a group, consider disabling privacy mode in BotFather so the bot can see normal messages

## Analysis style

ATLAS is designed to always return analysis in a structured format:

- **Bias**
- **Reasoning**
- **Alternative Scenario**
- **Risks**
- **Data Strength**

The bot should avoid:

- guaranteed profit language
- buy/sell commands
- overconfident claims
- unstructured replies

## Disclaimer

ATLAS is an educational market analysis tool. It does not provide financial advice, investment guarantees, or trading promises. All decisions remain the user’s responsibility.

## Roadmap idea

- **Phase 1**: Telegram bot + structured AI analysis
- **Phase 2**: Realtime market data integration
- **Phase 3**: Memory, richer analytics, and web dashboard

## Brand visual

A concept banner for ATLAS has been generated for product presentation.

---

Built for fast iteration, low budget, and high clarity.
