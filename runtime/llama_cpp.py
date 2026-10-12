from pathlib import Path

from .base import NAtlasRuntime, merge_system, validate_messages


class LlamaCppRuntime(NAtlasRuntime):
    """Local N-ATLaS GGUF runtime using llama.cpp."""

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
        temperature: float = 0.2,
        max_tokens: int = 256,
        verbose: bool = False,
    ):
        if not model_path:
            raise ValueError("NATLAS_MODEL_PATH is not configured.")

        model = Path(model_path)

        if not model.exists():
            raise FileNotFoundError(
                f"N-ATLaS model not found: {model}"
            )

        self.model_path = str(model)
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.temperature = temperature
        self.max_tokens = max_tokens

        from llama_cpp import Llama

        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_gpu_layers=self.n_gpu_layers,
            verbose=verbose,
        )

    def generate(self, prompt: str, **options) -> str:
        return self.chat([{"role": "user", "content": prompt}], **options)

    def chat(
        self,
        messages: list[dict],
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a reply from the local N-ATLaS GGUF model."""

        system, conversation = merge_system(validate_messages(messages), system)
        payload = ([{"role": "system", "content": system}] if system else []) + conversation

        response = self.llm.create_chat_completion(
            messages=payload,
            temperature=(
                self.temperature if temperature is None else temperature
            ),
            max_tokens=self.max_tokens if max_tokens is None else max_tokens,
        )

        return response["choices"][0]["message"]["content"] or ""
