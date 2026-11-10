"""The support bot, shared by the eval run and the live chat CLI."""

import os
import threading
import time

from google import genai
from google.genai import types

# AI Studio free tier: https://aistudio.google.com/apikey
MODEL = "gemini-3.5-flash-lite"

SYSTEM_PROMPT = (
    "You are a helpful customer support agent for an e-commerce company. "
    "Be empathetic but efficient. Ask clarifying questions when needed. "
    "If you can resolve the issue, do so. If you need to escalate, "
    "explain why and what the customer should expect next."
)

# The free tier allows roughly 15 requests per minute. One call every 5 seconds
# keeps a dataset run near 12. The live chat CLI sets this to 0.
REQUEST_INTERVAL_SECONDS = 5.0

# A stuck socket fails the case instead of hanging the whole run.
GEMINI_TIMEOUT_MS = 60_000

_client: genai.Client | None = None
_pace_lock = threading.Lock()
_last_request_at = 0.0


def get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise SystemExit("Set GEMINI_API_KEY to your Google AI Studio key, then rerun.")
        _client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
        )
    return _client


def pace() -> None:
    """Hold the next Gemini call until REQUEST_INTERVAL_SECONDS has passed."""
    global _last_request_at
    with _pace_lock:
        wait = REQUEST_INTERVAL_SECONDS - (time.monotonic() - _last_request_at)
        if _last_request_at and wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def complete(system: str, contents: list[dict], temperature: float) -> str:
    """One paced Gemini call."""
    pace()
    response = get_client().models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
        ),
    )
    return response.text or ""


def reply(
    customer_message: str,
    history: list[dict] | None = None,
    temperature: float = 0.0,
) -> str:
    """Answer one customer message.

    `history` is prior turns as {"role": "user" | "assistant", "content": str}.
    Gemini calls the assistant role "model".
    """
    contents = [
        {
            "role": "model" if turn["role"] == "assistant" else "user",
            "parts": [{"text": turn["content"]}],
        }
        for turn in (history or [])
    ]
    contents.append({"role": "user", "parts": [{"text": customer_message}]})
    return complete(SYSTEM_PROMPT, contents, temperature)
