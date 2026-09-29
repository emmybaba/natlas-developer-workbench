import json
import os
import time

import requests

from .base import NAtlasRuntime


class GradioRuntime(NAtlasRuntime):
    """Runtime for an N-ATLaS Gradio inference endpoint."""

    def __init__(
        self,
        base_url: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        json_mode: bool = False,
        poll_interval: float = 1.0,
        timeout: int = 120,
    ):
        self.base_url = (
            base_url
            or os.getenv("NATLAS_GRADIO_BASE_URL")
        )

        if not self.base_url:
            raise ValueError(
                "NATLAS_GRADIO_BASE_URL is not configured."
            )

        self.base_url = self.base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.json_mode = json_mode
        self.poll_interval = poll_interval
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        """Generate a response from N-ATLaS through Gradio."""

        messages = [
            {
                "role": "user",
                "content": prompt,
            }
        ]

        body = {
            "data": [
                json.dumps(messages),
                self.temperature,
                self.max_tokens,
                self.json_mode,
            ]
        }

        response = requests.post(
            f"{self.base_url}/gradio_api/call/generate",
            json=body,
            timeout=30,
        )

        response.raise_for_status()

        event_id = response.json()["event_id"]

        return self._wait_for_result(event_id)

    def _wait_for_result(self, event_id: str) -> str:
        """Poll the Gradio event until generation completes."""

        start_time = time.time()

        while time.time() - start_time < self.timeout:
            response = requests.get(
                f"{self.base_url}/gradio_api/call/generate/{event_id}",
                timeout=30,
            )

            response.raise_for_status()

            result = response.text

            if "event: complete" in result:
                return self._parse_result(result)

            if "event: error" in result:
                raise RuntimeError(
                    f"N-ATLaS generation failed: {result}"
                )

            time.sleep(self.poll_interval)

        raise TimeoutError(
            "Timed out waiting for the N-ATLaS generation response."
        )

    @staticmethod
    def _parse_result(result: str) -> str:
        """Extract generated text from the Gradio SSE response."""

        for line in result.splitlines():
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                response_data = json.loads(payload[0])

                return response_data.get("text", "")

        raise RuntimeError(
            "Completed N-ATLaS response did not contain data."
        )
