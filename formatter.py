import re
import logging

logger = logging.getLogger(__name__)

FORBIDDEN_WORDS = [
    "pasti", "dijamin", "guaranteed", "100%",
    "beli sekarang", "jual sekarang", "buy now", "sell now",
    "will definitely", "pasti untung", "pasti naik", "pasti turun",
]

DISCLAIMER_ID = "⚠️ Analisa konteks saja. Bukan rekomendasi transaksi."
DISCLAIMER_EN = "⚠️ Analysis only. Not financial advice."

MAX_OUTPUT_LENGTH = 1200


def post_process(text: str, lang: str = "id") -> str:
    """
    Safety post-processor:
    1. Check forbidden words
    2. Enforce max length
    3. Ensure disclaimer present
    """
    if not text:
        return _fallback(lang)

    # Replace forbidden words
    for word in FORBIDDEN_WORDS:
        if word.lower() in text.lower():
            logger.warning(f"Forbidden word found in output: '{word}'")
            text = re.sub(
                re.escape(word),
                "[dihapus]" if lang == "id" else "[removed]",
                text,
                flags=re.IGNORECASE,
            )

    # Enforce max length
    if len(text) > MAX_OUTPUT_LENGTH:
        text = text[:MAX_OUTPUT_LENGTH] + "..."
        logger.warning("Output truncated due to length")

    # Ensure disclaimer present
    disclaimer = DISCLAIMER_EN if lang == "en" else DISCLAIMER_ID
    if disclaimer not in text:
        text = text + f"\n\n{disclaimer}"

    return text


def _fallback(lang: str) -> str:
    if lang == "en":
        return "ATLAS could not generate analysis at this time. Please try again."
    return "ATLAS tidak dapat menghasilkan analisa saat ini. Silakan coba lagi."


def safe_to_send(text: str) -> bool:
    """Final gate before sending to Telegram."""
    if not text or len(text) < 50:
        return False
    # Robust disclaimer check — look for key phrases in both languages
    disclaimer_present = (
        "Bukan rekomendasi" in text
        or "Not financial advice" in text
        or "⚠️" in text  # Fallback: presence of warning emoji
    )
    if not disclaimer_present:
        logger.error("safe_to_send blocked: disclaimer missing")
        return False
    return True
