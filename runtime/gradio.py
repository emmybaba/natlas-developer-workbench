import json
import os

from gradio_client import Client

from .base import NAtlasRuntime, compose_prompt


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

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a response through the Gradio client."""

        return self.chat(
            [{"role": "user", "content": prompt}],
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def chat(
        self,
        messages: list[dict],
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a conversation through the Gradio client.

        The community Space's handling of a ``system`` role has not been
        verified, so a system instruction is folded into the first user
        message. The Space receives the whole ``messages`` list; whether it
        makes use of earlier turns depends on that Space.
        """

        if self._client is None:
            self._client = Client(self.base_url)

        messages = [dict(m) for m in messages]

        if system and system.strip():
            for message in messages:
                if message["role"] == "user":
                    message["content"] = compose_prompt(
                        message["content"], system
                    )
                    break

        result = self._client.predict(
            messages_json=json.dumps(messages),
            temperature=(
                self.temperature if temperature is None else temperature
            ),
            max_tokens=(
                self.max_tokens if max_tokens is None else max_tokens
            ),
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
