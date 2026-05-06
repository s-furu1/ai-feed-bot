from __future__ import annotations

import json
import urllib.error
import urllib.request


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int = 300,
        keep_alive: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.keep_alive = keep_alive

    def generate(self, prompt: str) -> str:
        url = f"{self.base_url}/api/generate"
        body: dict[str, object] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if self.keep_alive:
            body["keep_alive"] = self.keep_alive
        payload = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise OllamaError(f"Ollama request failed: {exc}") from exc
        generated = body.get("response")
        if not isinstance(generated, str):
            raise OllamaError("Ollama response did not include text")
        return generated

