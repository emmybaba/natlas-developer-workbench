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
        model_path=None,
        n_ctx=4096,
        n_gpu_layers=-1,
    ):
        self.runtime = runtime or self._create_runtime(
            runtime_type=runtime_type,
            base_url=base_url,
            api_key=api_key,
            model=model,
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
        )

    def _create_runtime(
        self,
        runtime_type=None,
        base_url=None,
        api_key=None,
        model=None,
        model_path=None,
        n_ctx=4096,
        n_gpu_layers=-1,
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

        if runtime_type == "llama_cpp":
            from runtime.llama_cpp import LlamaCppRuntime

            return LlamaCppRuntime(
                model_path=(
                    model_path
                    or os.getenv("NATLAS_MODEL_PATH")
                ),
                n_ctx=int(
                    os.getenv("NATLAS_N_CTX", n_ctx)
                ),
                n_gpu_layers=int(
                    os.getenv(
                        "NATLAS_N_GPU_LAYERS",
                        n_gpu_layers,
                    )
                ),
            )
        raise ValueError(
            f"Unsupported N-ATLaS runtime: {runtime_type}"
        )

    def generate(self, prompt: str) -> str:
        """Generate a response from N-ATLaS."""

        return self.runtime.generate(prompt)