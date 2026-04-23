"""Quick-title generation for conversations.

Uses a small/fast OpenAI-compatible model (configurable, defaults to
``VLLM_TITLE_MODEL`` env var or falls back to ``gpt-5.4-mini``) via the same
base URL + API key as the main vLLM endpoint. Non-streaming, <50 token
output — this is the "short, punchy" summarizer mentioned in Ant Design X.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from app.core.config import Settings

logger = logging.getLogger(__name__)

TITLE_SYSTEM = (
    "你是一个会话摘要助手。阅读用户提问和助手回答，用 6~14 个汉字给这段对话取一个简短、"
    "具体、中文标题，不要加引号、书名号或标点结尾。仅输出标题本身，不要解释。"
)


def _fast_model(settings: Settings) -> str:
    # Allow override via env, otherwise default to the fast mini model.
    import os

    return os.getenv("VLLM_TITLE_MODEL") or "gpt-5.4-mini"


def generate_conversation_title(
    settings: Settings,
    *,
    user_message: str,
    assistant_message: str,
    max_tokens: int = 32,
    timeout: float = 15.0,
) -> str:
    """Call the fast model synchronously and return the resulting title.

    Raises the original urllib/JSON error on failure; caller decides whether
    to fall back to the first user message.
    """
    endpoint = f"{settings.vllm_base_url.rstrip('/')}/chat/completions"
    body = {
        "model": _fast_model(settings),
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "stream": False,
        "messages": [
            {"role": "system", "content": TITLE_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"用户提问：{user_message.strip()[:500]}\n"
                    f"助手回答（节选）：{assistant_message.strip()[:800]}\n"
                    f"请输出标题："
                ),
            },
        ],
    }
    headers = {"Content-Type": "application/json"}
    if settings.vllm_api_key:
        headers["Authorization"] = f"Bearer {settings.vllm_api_key}"
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("no_choices_in_title_response")
    content = (choices[0].get("message") or {}).get("content") or ""
    # Normalize: strip surrounding quotes/punctuation, cap length.
    title = content.strip().strip("“”\"'《》").rstrip("。！？!?.").strip()
    if not title:
        raise ValueError("empty_title")
    return title[:30]
