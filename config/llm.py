# config/llm.py
import time

from groq import BadRequestError, Groq, RateLimitError

from config.logger import setup_logger
from config.settings import settings

logger = setup_logger("llm")
client = Groq(api_key=settings.groq_api_key)

# Groq rate limits are per model, so on a 429 we fall through to the next one.
FALLBACK_MODELS = ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]
MAX_WAIT = 60  # free tier is 8k tokens/minute per model, so a short wait usually clears every model


def _retry_after(e: RateLimitError) -> float:
    try:
        return float(e.response.headers.get("retry-after", MAX_WAIT))
    except (TypeError, ValueError):
        return MAX_WAIT


def chat(**kwargs):
    """client.chat.completions.create with silent model fallback on rate limits.
    If every model is rate limited, waits for the soonest reset (<= MAX_WAIT) and tries all once more."""
    models = [settings.default_model] + [m for m in FALLBACK_MODELS if m != settings.default_model]
    for attempt in range(2):
        waits, last_err = [], None
        for model in models:
            extra = {"reasoning_format": "hidden"} if model.startswith("qwen/") else {}  # keep <think> out of answers
            try:
                return client.chat.completions.create(model=model, **kwargs, **extra)
            except RateLimitError as e:
                waits.append(_retry_after(e))
                last_err = e
                logger.warning(f"Rate limited on {model}, trying the next model")
            except BadRequestError as e:
                # Smaller models sometimes return empty output in JSON mode; another model usually succeeds.
                if "json_validate_failed" not in str(e):
                    raise
                last_err = e
                logger.warning(f"{model} returned invalid JSON, trying the next model")
        if attempt == 0 and waits and min(waits) <= MAX_WAIT:
            logger.warning(f"All models busy; waiting {min(waits):.0f}s for the rate limit to reset")
            time.sleep(min(waits) + 1)
        else:
            break
    raise last_err
