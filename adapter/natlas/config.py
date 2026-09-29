import os


class NAtlasConfig:
    """Configuration for connecting to an N-ATLaS inference endpoint."""

    def __init__(
        self,
        base_url=None,
        api_key=None,
        model=None,
    ):
        self.base_url = base_url or os.getenv("NATLAS_BASE_URL")
        self.api_key = api_key or os.getenv("NATLAS_API_KEY")
        self.model = model or os.getenv("NATLAS_MODEL", "N-ATLaS")

    def validate(self):
        """Validate the minimum configuration required for inference."""

        if not self.base_url:
            raise ValueError(
                "NATLAS_BASE_URL is not configured."
            )

        if not self.api_key:
            raise ValueError(
                "NATLAS_API_KEY is not configured."
            )