from openai import OpenAI

from .base import NAtlasRuntime


class OpenAICompatibleRuntime(NAtlasRuntime):
    """Runtime for an OpenAI-compatible N-ATLaS inference endpoint."""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.model = model

    def generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        return response.choices[0].message.content or ""
