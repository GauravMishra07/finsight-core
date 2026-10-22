# config/llm.py
from groq import Groq, RateLimitError

from config.logger import setup_logger
from config.settings import settings

logger = setup_logger("llm")
client = Groq(api_key=settings.groq_api_key)

# Groq rate limits are per model, so on a 429 we fall through to the next one.
FALLBACK_MODELS = ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]


def chat(**kwargs):
    """client.chat.completions.create with silent model fallback on rate limits."""
    models = [settings.default_model] + [m for m in FALLBACK_MODELS if m != settings.default_model]
    for i, model in enumerate(models):
        extra = {"reasoning_format": "hidden"} if model.startswith("qwen/") else {}  # keep <think> out of answers
        try:
            return client.chat.completions.create(model=model, **kwargs, **extra)
        except RateLimitError:
            if i == len(models) - 1:
                raise
            logger.warning(f"Rate limited on {model}, switching to {models[i + 1]}")
