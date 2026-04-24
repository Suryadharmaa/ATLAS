import time
import logging
from openai import OpenAI
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS, GROQ_TEMPERATURE

logger = logging.getLogger(__name__)

_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

FALLBACK_MESSAGE = (
    "ATLAS tidak dapat memproses analisa saat ini. "
    "Silakan ulangi dalam beberapa saat."
)


def call_groq(system_prompt: str, messages: list) -> str:
    """
    Send messages to Groq and return response text.
    Returns FALLBACK_MESSAGE on any failure.
    """
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    for attempt in range(2):  # Try max 2 times
        try:
            response = _client.chat.completions.create(
                model=GROQ_MODEL,
                messages=full_messages,
                max_tokens=GROQ_MAX_TOKENS,
                temperature=GROQ_TEMPERATURE,
            )

            choices = response.choices
            if not choices or not choices[0].message.content:
                logger.warning("Groq returned empty choices")
                return FALLBACK_MESSAGE

            result = choices[0].message.content.strip()

            if len(result) < 50:
                logger.warning(f"Groq response too short: {result}")
                return FALLBACK_MESSAGE

            return result

        except Exception as e:
            logger.error(f"Groq call attempt {attempt + 1} failed: {e}")
            if attempt == 0:
                time.sleep(3)  # Wait before retry

    return FALLBACK_MESSAGE
