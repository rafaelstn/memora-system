"""
Simula um push event do GitHub para testar o webhook de re-indexação.
Uso: python scripts/simulate_webhook.py [--no-sign]

Envia payload simulado para localhost:8000/api/webhooks/github
com assinatura HMAC válida usando GITHUB_WEBHOOK_SECRET do .env.
"""

import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

PAYLOAD = {
    "ref": "refs/heads/main",
    "repository": {
        "full_name": "memora",
        "clone_url": "https://github.com/example/memora.git",
    },
    "commits": [
        {
            "id": "abc123",
            "message": "feat: atualiza chunker com suporte a decorators",
            "added": ["app/core/new_module.py"],
            "modified": ["app/core/chunker.py", "app/core/embedder.py"],
            "removed": ["app/core/old_module.py"],
        }
    ],
}


def sign_payload(payload_bytes: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()


def main():
    no_sign = "--no-sign" in sys.argv
    payload_bytes = json.dumps(PAYLOAD).encode()

    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "push",
    }

    if not no_sign:
        if not WEBHOOK_SECRET:
            print("AVISO: GITHUB_WEBHOOK_SECRET nao definido no .env")
            print("Use --no-sign para testar sem assinatura")
            sys.exit(1)
        headers["X-Hub-Signature-256"] = sign_payload(payload_bytes, WEBHOOK_SECRET)
        print(f"Assinatura gerada com secret: {WEBHOOK_SECRET[:8]}...")
    else:
        print("Enviando sem assinatura (--no-sign)")

    url = f"{API_BASE}/api/webhooks/github"
    print(f"Enviando para: {url}")
    print(f"Payload: {json.dumps(PAYLOAD, indent=2)}")
    print("-" * 60)

    try:
        response = httpx.post(url, content=payload_bytes, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "processing":
                print("\nWebhook aceito! Re-indexacao em background.")
                print(f"  Arquivos para re-indexar: {data.get('files_to_reindex')}")
                print(f"  Arquivos para remover: {data.get('files_to_remove')}")
            elif data.get("status") == "ignored":
                print(f"\nWebhook ignorado: {data.get('reason', data.get('event'))}")
        elif response.status_code == 401:
            print("\nAssinatura invalida! Verifique GITHUB_WEBHOOK_SECRET.")
    except httpx.ConnectError:
        print(f"\nErro: nao foi possivel conectar em {API_BASE}")
        print("Certifique-se de que o servidor esta rodando: uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
