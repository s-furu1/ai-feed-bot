from __future__ import annotations

import json
from unittest import mock

from app.ollama.client import OllamaClient


def test_ollama_client_default_timeout_is_300():
    client = OllamaClient("http://ollama:11434", "qwen3.5:9b")
    assert client.timeout == 300


def test_ollama_client_custom_timeout_is_used_in_request():
    client = OllamaClient(
        "http://ollama:11434", "qwen3.5:9b", timeout=120, keep_alive="5m"
    )

    fake_response = mock.MagicMock()
    fake_response.read.return_value = json.dumps({"response": "hi"}).encode("utf-8")
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = False

    with mock.patch("app.ollama.client.urllib.request.urlopen", return_value=fake_response) as opener:
        result = client.generate("hello")

    assert result == "hi"
    _, kwargs = opener.call_args
    assert kwargs["timeout"] == 120
    request = opener.call_args.args[0]
    body = json.loads(request.data.decode("utf-8"))
    assert body["model"] == "qwen3.5:9b"
    assert body["prompt"] == "hello"
    assert body["keep_alive"] == "5m"
    assert body["stream"] is False


def test_ollama_client_omits_keep_alive_when_not_set():
    client = OllamaClient("http://ollama:11434", "qwen3.5:9b", timeout=60)

    fake_response = mock.MagicMock()
    fake_response.read.return_value = json.dumps({"response": "ok"}).encode("utf-8")
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = False

    with mock.patch("app.ollama.client.urllib.request.urlopen", return_value=fake_response) as opener:
        client.generate("p")

    request = opener.call_args.args[0]
    body = json.loads(request.data.decode("utf-8"))
    assert "keep_alive" not in body
