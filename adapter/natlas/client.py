from openai import OpenAI

from .config import NAtlasConfig


class NAtlasClient:
    """Client for interacting with an N-ATLaS inference endpoint."""

    def __init__(self, config: NAtlasConfig):
        config.validate()

        self.config = config

        self.client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
        )

    def chat(self, prompt: str) -> str:
        """Send a prompt to N-ATLaS and return the generated response."""

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        return response.choices[0].message.content or ""