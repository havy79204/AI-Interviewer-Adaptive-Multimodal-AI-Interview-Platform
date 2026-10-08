"""
Adapter: LLMClient (core/llm.py) -> llm_call(system_prompt, user_prompt, schema).

- Dùng ChatPromptTemplate nên phải escape { } (nội dung CV/JD có thể chứa ngoặc nhọn,
  ví dụ đoạn code, nếu không sẽ lỗi 'missing input variable').
- Một số model open-weight (Groq/OpenRouter) hay lỗi tool-calling khi structured output:
  tự thử lại 1 lần bằng structured_method="json_mode". Với Anthropic thường không cần.
"""
import logging

logger = logging.getLogger(__name__)

_TOOL_CALL_ERRORS = ("tool call validation failed", "was not in request.tools", "tool_use_failed")


def _escape_braces(text: str) -> str:
    return text.replace("{", "{{").replace("}", "}}")


import time

def _is_rate_limit(e: Exception) -> bool:
    if "ratelimit" in type(e).__name__.lower() or getattr(e, "status_code", None) == 429:
        return True
    msg = str(e).lower()
    return any(k in msg for k in ("rate limit", "rate_limit", "error code: 429",
                                  "too many requests", "tokens per minute"))


def _with_rate_limit_retry(fn, wait: int = 20, max_retries: int = 5):
    """Gặp rate limit thì chờ `wait` giây rồi gọi lại (tối đa max_retries lần)."""
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            if not _is_rate_limit(e) or attempt == max_retries:
                raise
            logger.warning("Rate limit, chờ %ss rồi thử lại (%s/%s)", wait, attempt + 1, max_retries)
            time.sleep(wait)


def make_llm_call(client=None, max_tokens: int = 10000, temperature: float = 0.2,
                  rate_limit_wait: int = 20, rate_limit_retries: int = 5):
    if client is None:
        from core.llm import LLMClient
        client = LLMClient()
    from langchain_core.prompts import ChatPromptTemplate

    def _prompt(system, user, suffix=""):
        return ChatPromptTemplate.from_messages([
            ("system", _escape_braces(system)),
            ("human", _escape_braces(user) + suffix),
        ])

    def _run(prompt, schema, **kw):
        # retries=1: để lỗi rate limit nổi lên ngay, không bị retry tức thì làm tốn thêm lượt gọi
        return _with_rate_limit_retry(
            lambda: client.invoke_with_retries(
                prompt, max_tokens=max_tokens, temperature=temperature,
                output_schema=schema, retries=1, **kw),
            wait=rate_limit_wait, max_retries=rate_limit_retries,
        )

    def llm_call(system, user, schema):
        try:
            return _run(_prompt(system, user), schema)
        except Exception as e:
            if not any(k in str(e).lower() for k in _TOOL_CALL_ERRORS):
                raise
            logger.warning("Structured output lỗi, thử lại bằng json_mode: %s", str(e)[:200])
            return _run(_prompt(system, user, "\n\nTrả lời CHỈ bằng một object json hợp lệ, không thêm chữ nào khác."),
                        schema, structured_method="json_mode")

    return llm_call
