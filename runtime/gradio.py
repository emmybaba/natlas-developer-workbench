import json
import os

from gradio_client import Client

from .base import NAtlasRuntime


class GradioRuntime(NAtlasRuntime):
    """Runtime for an N-ATLaS Gradio inference endpoint."""

    def __init__(
        self,
        base_url: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        json_mode: bool = False,
        timeout: int = 120,
    ):
        self.base_url = (
            base_url or os.getenv("NATLAS_GRADIO_BASE_URL")
        )

        if not self.base_url:
            raise ValueError(
                "NATLAS_GRADIO_BASE_URL is not configured."
            )

        self.base_url = self.base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.json_mode = json_mode
        self.timeout = timeout
        self._client = None

    def generate(self, prompt: str) -> str:
        """Generate a response through the Gradio client."""

        if self._client is None:
            self._client = Client(self.base_url)

        messages = [{"role": "user", "content": prompt}]

        result = self._client.predict(
            messages_json=json.dumps(messages),
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            json_mode=self.json_mode,
            api_name="/generate",
        )

        if isinstance(result, dict):
            return str(result.get("text", result))

        if isinstance(result, str):
            try:
                payload = json.loads(result)
            except json.JSONDecodeError:
                return result

            if isinstance(payload, dict):
                return str(payload.get("text", result))

        return str(result)
