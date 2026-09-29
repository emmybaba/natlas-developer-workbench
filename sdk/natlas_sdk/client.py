import os

from adapter.natlas.config import NAtlasConfig
from adapter.natlas.client import NAtlasClient


class NAtlas:
    """Public developer-facing SDK for N-ATLaS."""

    def __init__(
        self,
        base_url=None,
        api_key=None,
        model=None,
    ):
        config = NAtlasConfig(
            base_url=base_url or os.getenv("NATLAS_BASE_URL"),
            api_key=api_key or os.getenv("NATLAS_API_KEY"),
            model=model or os.getenv("NATLAS_MODEL", "N-ATLaS"),
        )

        self._client = NAtlasClient(config)

    def generate(self, prompt: str) -> str:
        """Generate a response from N-ATLaS."""

        return self._client.chat(prompt)