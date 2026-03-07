import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)

WEBHOOK_URL = "/api/webhooks/github"
SECRET = "test-secret-key"


def _sign_payload(payload: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def _make_push_payload(
    ref: str = "refs/heads/main",
    repo_name: str = "org/repo",
    added: list[str] | None = None,
    modified: list[str] | None = None,
    removed: list[str] | None = None,
) -> dict:
    return {
        "ref": ref,
        "repository": {"full_name": repo_name, "clone_url": f"https://github.com/{repo_name}.git"},
        "commits": [
            {
                "added": added or [],
                "modified": modified or [],
                "removed": removed or [],
            }
        ],
    }


@patch("app.api.routes.webhooks.settings")
def test_rejects_missing_signature(mock_settings):
    mock_settings.github_webhook_secret = SECRET
    payload = json.dumps(_make_push_payload()).encode()

    response = client.post(
        WEBHOOK_URL,
        content=payload,
        headers={"X-GitHub-Event": "push", "Content-Type": "application/json"},
    )
    assert response.status_code == 401


@patch("app.api.routes.webhooks.settings")
def test_rejects_invalid_signature(mock_settings):
    mock_settings.github_webhook_secret = SECRET
    payload = json.dumps(_make_push_payload()).encode()

    response = client.post(
        WEBHOOK_URL,
        content=payload,
        headers={
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": "sha256=invalid",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 401


@patch("app.api.routes.webhooks._process_push")
@patch("app.api.routes.webhooks.settings")
def test_accepts_valid_signature(mock_settings, mock_process):
    mock_settings.github_webhook_secret = SECRET
    payload = json.dumps(_make_push_payload(modified=["app/main.py"])).encode()
    sig = _sign_payload(payload, SECRET)

    response = client.post(
        WEBHOOK_URL,
        content=payload,
        headers={
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processing"


@patch("app.api.routes.webhooks.settings")
def test_ignores_non_main_branch(mock_settings):
    mock_settings.github_webhook_secret = ""
    payload = _make_push_payload(ref="refs/heads/feature/xyz", modified=["app/main.py"])

    response = client.post(
        WEBHOOK_URL,
        json=payload,
        headers={"X-GitHub-Event": "push"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert "not main/master" in response.json()["reason"]


@patch("app.api.routes.webhooks.settings")
def test_ignores_non_python_files(mock_settings):
    mock_settings.github_webhook_secret = ""
    payload = _make_push_payload(modified=["README.md", "docs/guide.txt", "style.css"])

    response = client.post(
        WEBHOOK_URL,
        json=payload,
        headers={"X-GitHub-Event": "push"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert "no Python files" in response.json()["reason"]


@patch("app.api.routes.webhooks.settings")
def test_processes_only_py_files(mock_settings):
    mock_settings.github_webhook_secret = ""
    payload = _make_push_payload(
        modified=["app/main.py", "README.md"],
        added=["app/new_module.py"],
        removed=["app/old.py"],
    )

    response = client.post(
        WEBHOOK_URL,
        json=payload,
        headers={"X-GitHub-Event": "push"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert data["files_to_reindex"] == 2  # main.py + new_module.py
    assert data["files_to_remove"] == 1  # old.py
