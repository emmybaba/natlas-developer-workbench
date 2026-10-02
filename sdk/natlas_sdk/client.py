import os

from runtime.gradio import GradioRuntime
from runtime.openai_compatible import OpenAICompatibleRuntime


class NAtlas:
    """Public developer-facing SDK for N-ATLaS."""

    def __init__(
        self,
        runtime=None,
        runtime_type=None,
        base_url=None,
        api_key=None,
        model=None,
    ):
        self.runtime = runtime or self._create_runtime(
            runtime_type=runtime_type,
            base_url=base_url,
            api_key=api_key,
            model=model,
        )

    def _create_runtime(
        self,
        runtime_type=None,
        base_url=None,
        api_key=None,
        model=None,
    ):
        runtime_type = (
            runtime_type
            or os.getenv("NATLAS_RUNTIME", "gradio")
        ).lower()

        if runtime_type == "gradio":
            return GradioRuntime(
                base_url=(
                    base_url
                    or os.getenv("NATLAS_GRADIO_BASE_URL")
                )
            )

        if runtime_type == "openai":
            return OpenAICompatibleRuntime(
                base_url=(
                    base_url
                    or os.getenv("NATLAS_BASE_URL")
                ),
                api_key=(
                    api_key
                    or os.getenv("NATLAS_API_KEY")
                ),
                model=(
                    model
                    or os.getenv("NATLAS_MODEL", "N-ATLaS")
                ),
            )

        raise ValueError(
            f"Unsupported N-ATLaS runtime: {runtime_type}"
        )

    def generate(self, prompt: str) -> str:
        """Generate a response from N-ATLaS."""

        return self.runtime.generate(prompt)