import logging
from typing import Iterator

from .pricing import calc_cost

logger = logging.getLogger(__name__)


class AnthropicClient:
    def __init__(self, api_key: str):
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        max_tokens: int = 2048,
    ) -> dict:
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost_usd = calc_cost(model, input_tokens, output_tokens)

        return {
            "text": response.content[0].text,
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
        with self._client.messages.stream(
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
            cost_usd = calc_cost(model, input_tokens, output_tokens)
            yield None, {
                "model": model,
                "tokens": input_tokens + output_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": round(cost_usd, 8),
            }
