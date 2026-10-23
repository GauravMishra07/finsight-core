# tests/test_llm.py — offline: config.llm.chat retries and falls back with a stubbed Groq client.
import httpx
from groq import BadRequestError, RateLimitError

from config import llm

REQ = httpx.Request("POST", "https://api.groq.com")


def bad_json():
    return BadRequestError("json_validate_failed", response=httpx.Response(400, request=REQ), body=None)


def rate_limited():
    return RateLimitError("429", response=httpx.Response(429, request=REQ, headers={"retry-after": "0"}), body=None)


def run(outcomes):
    """outcomes: one per call; an exception is raised, anything else is returned. Returns (result, models called)."""
    calls, it = [], iter(outcomes)

    def create(model, **_):
        calls.append(model)
        o = next(it)
        if isinstance(o, Exception):
            raise o
        return o

    llm.client.chat.completions.create = create
    try:
        return llm.chat(messages=[]), calls
    except Exception as e:
        return e, calls


def test_json_failure_retries_same_model():
    res, calls = run([bad_json(), "ok"])
    assert res == "ok" and calls[0] == calls[1] == llm.settings.default_model


def test_json_failure_twice_falls_back():
    res, calls = run([bad_json(), bad_json(), "ok"])
    assert res == "ok" and calls[2] != calls[0]


def test_rate_limit_skips_retry_on_same_model():
    res, calls = run([rate_limited(), "ok"])
    assert res == "ok" and calls[1] != calls[0]


def test_other_bad_request_raises():
    other = BadRequestError("context too long", response=httpx.Response(400, request=REQ), body=None)
    res, calls = run([other])
    assert res is other and len(calls) == 1


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("llm: all checks passed")
