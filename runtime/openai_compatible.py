from openai import OpenAI

from .base import NAtlasRuntime, merge_system, validate_messages


class OpenAICompatibleRuntime(NAtlasRuntime):
    """Runtime for an OpenAI-compatible N-ATLaS inference endpoint."""

    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.model = model

    def generate(self, prompt: str, **options) -> str:
        return self.chat([{"role": "user", "content": prompt}], **options)

    def chat(
        self,
        messages: list[dict],
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        system, conversation = merge_system(validate_messages(messages), system)
        payload = ([{"role": "system", "content": system}] if system else []) + conversation

        params = {"model": self.model, "messages": payload}

        if temperature is not None:
            params["temperature"] = temperature

        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        response = self.client.chat.completions.create(**params)

        return response.choices[0].message.content or ""
