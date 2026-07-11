"""The model seam.

Every model call in After Japhy passes through this module. Provider,
endpoint, and model name live here and nowhere else, so switching engines
is editing one file. (WVP ruling, July 10 2026: no piece may be
structurally dependent on any one AI vendor.)

The persona is tuned against Claude's service tropism. If MODEL changes,
re-run the adversarial persona tests from the project brief (pleas for
help, requests to summarize, emotional bait) before shipping.
"""

import os
from anthropic import Anthropic

PROVIDER = "anthropic"
MODEL = "claude-haiku-4-5-20251001"

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        _client = Anthropic(api_key=api_key)
    return _client


def complete(messages, system=None, max_tokens=400):
    """Run one completion. Returns the response text.

    messages: list of {"role": ..., "content": ...}
    system:   optional system prompt string
    """
    kwargs = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system

    response = _get_client().messages.create(**kwargs)
    return response.content[0].text
