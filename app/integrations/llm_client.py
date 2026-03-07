import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Preços por 1M tokens (USD)
MODEL_PRICING = {
    # Anthropic
    "claude-haiku-4-5-20251001": {"input": 1.00, "output": 5.00},
    "claude-sonnet-4-5-20250514": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    # OpenAI
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
}

_anthropic_client = None
_openai_client = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic
        _anthropic_client = Anthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _calc_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model, {"input": 1.00, "output": 5.00})
    return (input_tokens / 1_000_000) * pricing["input"] + \
           (output_tokens / 1_000_000) * pricing["output"]


def call_claude(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    max_tokens: int = 2048,
) -> dict:
    client = _get_anthropic_client()
    model = model or settings.claude_model_fast

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    total_tokens = input_tokens + output_tokens
    cost_usd = _calc_cost(model, input_tokens, output_tokens)

    logger.info(f"Claude ({model}): {input_tokens} in / {output_tokens} out — ${cost_usd:.6f}")

    return {
        "text": response.content[0].text,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(cost_usd, 6),
    }


def call_openai(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    max_tokens: int = 2048,
) -> dict:
    client = _get_openai_client()
    model = model or settings.openai_model_fast

    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    total_tokens = input_tokens + output_tokens
    cost_usd = _calc_cost(model, input_tokens, output_tokens)

    logger.info(f"OpenAI ({model}): {input_tokens} in / {output_tokens} out — ${cost_usd:.6f}")

    return {
        "text": response.choices[0].message.content,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": round(cost_usd, 6),
    }


def call_llm(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    max_tokens: int = 2048,
) -> dict:
    provider = settings.llm_provider.lower()

    if provider == "anthropic":
        return call_claude(system_prompt, user_message, model, max_tokens)
    elif provider == "openai":
        return call_openai(system_prompt, user_message, model, max_tokens)
    else:
        raise ValueError(f"Provider LLM desconhecido: {provider}")


def stream_openai(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    max_tokens: int = 2048,
):
    """Yield text chunks from OpenAI streaming response. Returns (chunk, meta) tuples.
    meta is None for text chunks, dict with tokens/cost for the final chunk."""
    client = _get_openai_client()
    model = model or settings.openai_model_fast

    stream = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        stream=True,
        stream_options={"include_usage": True},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content, None

        if chunk.usage:
            input_tokens = chunk.usage.prompt_tokens
            output_tokens = chunk.usage.completion_tokens
            cost_usd = _calc_cost(model, input_tokens, output_tokens)
            yield None, {
                "model": model,
                "tokens": input_tokens + output_tokens,
                "cost_usd": round(cost_usd, 6),
            }


def stream_claude(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    max_tokens: int = 2048,
):
    """Yield text chunks from Anthropic streaming response."""
    client = _get_anthropic_client()
    model = model or settings.claude_model_fast

    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            yield text, None

        response = stream.get_final_message()
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost_usd = _calc_cost(model, input_tokens, output_tokens)
        yield None, {
            "model": model,
            "tokens": input_tokens + output_tokens,
            "cost_usd": round(cost_usd, 6),
        }


def stream_llm(
    system_prompt: str,
    user_message: str,
    model: str | None = None,
    max_tokens: int = 2048,
):
    """Unified streaming — yields (text_chunk, meta) tuples."""
    provider = settings.llm_provider.lower()
    if provider == "openai":
        yield from stream_openai(system_prompt, user_message, model, max_tokens)
    elif provider == "anthropic":
        yield from stream_claude(system_prompt, user_message, model, max_tokens)
    else:
        raise ValueError(f"Provider LLM desconhecido: {provider}")
