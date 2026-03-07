import logging
from typing import Iterator

from .pricing import calc_cost

logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(self, api_key: str, base_url: str | None = None):
        from openai import OpenAI

        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)

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
                cost_usd = calc_cost(model, input_tokens, output_tokens)
                yield None, {
                    "model": model,
                    "tokens": input_tokens + output_tokens,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": round(cost_usd, 8),
                }
