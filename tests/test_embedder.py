from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_settings():
    with patch("app.core.embedder.settings") as mock:
        mock.openai_api_key = "sk-test-key"
        mock.embedding_model = "text-embedding-3-small"
        mock.embedding_batch_size = 2
        mock.usd_to_brl = 5.70
        yield mock


@pytest.fixture
def mock_openai_client():
    with patch("app.core.embedder.OpenAI") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        yield client


@pytest.fixture
def mock_tiktoken():
    with patch("app.core.embedder.tiktoken") as mock:
        encoder = MagicMock()
        encoder.encode.side_effect = lambda t: list(range(len(t.split())))
        encoder.decode.side_effect = lambda tokens: " ".join(f"word{i}" for i in tokens)
        mock.get_encoding.return_value = encoder
        yield encoder


def _make_embedding_response(count: int, dim: int = 1536):
    response = MagicMock()
    items = []
    for i in range(count):
        item = MagicMock()
        item.embedding = [0.1 * (i + 1)] * dim
        items.append(item)
    response.data = items
    return response


def test_embed_text_returns_1536_dims(mock_settings, mock_openai_client, mock_tiktoken):
    from app.core.embedder import Embedder

    mock_openai_client.embeddings.create.return_value = _make_embedding_response(1)

    embedder = Embedder()
    result = embedder.embed_text("Hello world")

    assert len(result) == 1536
    mock_openai_client.embeddings.create.assert_called_once()


def test_embed_batch_processes_in_batches(mock_settings, mock_openai_client, mock_tiktoken):
    from app.core.embedder import Embedder

    mock_openai_client.embeddings.create.side_effect = [
        _make_embedding_response(2),
        _make_embedding_response(1),
    ]

    embedder = Embedder()
    result = embedder.embed_batch(["text one", "text two", "text three"])

    assert len(result) == 3
    assert mock_openai_client.embeddings.create.call_count == 2


def test_estimate_cost(mock_settings, mock_openai_client, mock_tiktoken):
    from app.core.embedder import Embedder

    embedder = Embedder()
    cost = embedder.estimate_cost(["hello world", "foo bar baz"])

    assert cost["tokens_estimados"] > 0
    assert cost["custo_usd"] >= 0
    assert cost["custo_brl"] >= 0
    assert cost["custo_brl"] == pytest.approx(cost["custo_usd"] * 5.70, abs=0.01)


def test_missing_api_key_raises():
    with patch("app.core.embedder.settings") as mock:
        mock.openai_api_key = ""
        from app.core.embedder import Embedder
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            Embedder()
