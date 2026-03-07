import logging
from typing import Iterator

from .pricing import calc_cost

logger = logging.getLogger(__name__)


class GoogleClient:
    def __init__(self, api_key: str):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._genai = genai

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        max_tokens: int = 2048,
    ) -> dict:
        gen_model = self._genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt,
            generation_config=self._genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
            ),
        )

        response = gen_model.generate_content(user_message)

        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        cost_usd = calc_cost(model, input_tokens, output_tokens)

        return {
            "text": response.text,
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
        gen_model = self._genai.GenerativeModel(
            model_name=model,
            system_instruction=system_prompt,
            generation_config=self._genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
            ),
        )

        response = gen_model.generate_content(user_message, stream=True)

        total_input = 0
        total_output = 0
        for chunk in response:
            if chunk.text:
                yield chunk.text, None
            if chunk.usage_metadata:
                total_input = chunk.usage_metadata.prompt_token_count
                total_output = chunk.usage_metadata.candidates_token_count

        cost_usd = calc_cost(model, total_input, total_output)
        yield None, {
            "model": model,
            "tokens": total_input + total_output,
            "input_tokens": total_input,
            "output_tokens": total_output,
            "cost_usd": round(cost_usd, 8),
        }
