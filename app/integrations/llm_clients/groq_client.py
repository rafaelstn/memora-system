import logging
from typing import Iterator

from .pricing import calc_cost

logger = logging.getLogger(__name__)


class GroqClient:
    """Groq uses OpenAI-compatible API."""

    def __init__(self, api_key: str):
        from groq import Groq

        self._client = Groq(api_key=api_key)

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        max_tokens: int = 2048,
    ) -> dict:
        response = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost_usd = calc_cost(model, input_tokens, output_tokens)

        return {
            "text": response.choices[0].message.content,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": round(cost_usd, 8),
        }

    def stream(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        max_tokens: int = 2048,
    ) -> Iterator[tuple[str | None, dict | None]]:
        stream = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            stream=True,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        total_input = 0
        total_output = 0
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content, None
            if hasattr(chunk, "x_groq") and chunk.x_groq and hasattr(chunk.x_groq, "usage"):
                total_input = chunk.x_groq.usage.prompt_tokens
                total_output = chunk.x_groq.usage.completion_tokens

        cost_usd = calc_cost(model, total_input, total_output)
        yield None, {
            "model": model,
            "tokens": total_input + total_output,
            "input_tokens": total_input,
            "output_tokens": total_output,
            "cost_usd": round(cost_usd, 8),
        }
