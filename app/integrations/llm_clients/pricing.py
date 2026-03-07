# Preco por 1 token (USD). Atualizar conforme mudancas de preco dos provedores.
MODEL_PRICING: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input": 0.0000025, "output": 0.000010},
    "gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
    "gpt-4.1": {"input": 0.000002, "output": 0.000008},
    "gpt-4.1-mini": {"input": 0.0000004, "output": 0.0000016},
    "gpt-4.1-nano": {"input": 0.0000001, "output": 0.0000004},
    # Anthropic
    "claude-opus-4-5-20250514": {"input": 0.000015, "output": 0.000075},
    "claude-sonnet-4-5-20250514": {"input": 0.000003, "output": 0.000015},
    "claude-sonnet-4-6": {"input": 0.000003, "output": 0.000015},
    "claude-haiku-4-5-20251001": {"input": 0.0000008, "output": 0.000004},
    # Google
    "gemini-1.5-pro": {"input": 0.00000125, "output": 0.000005},
    "gemini-1.5-flash": {"input": 0.000000075, "output": 0.0000003},
    "gemini-2.0-flash": {"input": 0.0000001, "output": 0.0000004},
    # Groq (free tier)
    "llama-3.1-70b-versatile": {"input": 0.0, "output": 0.0},
    "llama-3.1-8b-instant": {"input": 0.0, "output": 0.0},
    "mixtral-8x7b-32768": {"input": 0.0, "output": 0.0},
}

# Modelos validos por provedor
PROVIDER_MODELS: dict[str, list[str]] = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"],
    "anthropic": [
        "claude-opus-4-5-20250514",
        "claude-sonnet-4-5-20250514",
        "claude-sonnet-4-6",
        "claude-haiku-4-5-20251001",
    ],
    "google": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash"],
    "groq": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
    "ollama": [],  # Ollama aceita qualquer modelo instalado
}


def calc_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    pricing = MODEL_PRICING.get(model_id, {"input": 0.0, "output": 0.0})
    return input_tokens * pricing["input"] + output_tokens * pricing["output"]
