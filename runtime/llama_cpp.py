from pathlib import Path

from .base import NAtlasRuntime


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

    def generate(self, prompt: str) -> str:
        """Generate a response from the local N-ATLaS GGUF model."""

        response = self.llm.create_chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        return response["choices"][0]["message"]["content"] or ""