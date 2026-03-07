import logging
from typing import Iterator

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434"
TIMEOUT = 60.0


class OllamaClient:
    def __init__(self, base_url: str | None = None):
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        max_tokens: int = 2048,
    ) -> dict:
        response = httpx.post(
            f"{self._base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
                "options": {"num_predict": max_tokens},
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        input_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)

        return {
            "text": data["message"]["content"],
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": 0.0,
        }

    def stream(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        max_tokens: int = 2048,
    ) -> Iterator[tuple[str | None, dict | None]]:
        with httpx.stream(
            "POST",
            f"{self._base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "stream": True,
                "options": {"num_predict": max_tokens},
            },
            timeout=TIMEOUT,
        ) as response:
            response.raise_for_status()
            import json

            total_input = 0
            total_output = 0
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if data.get("message", {}).get("content"):
                    yield data["message"]["content"], None
                if data.get("done"):
                    total_input = data.get("prompt_eval_count", 0)
                    total_output = data.get("eval_count", 0)

            yield None, {
                "model": model,
                "tokens": total_input + total_output,
                "input_tokens": total_input,
                "output_tokens": total_output,
                "cost_usd": 0.0,
            }
