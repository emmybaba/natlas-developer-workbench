import os
import time

from .conversation import Conversation

RUNTIME_TYPES = ("gradio", "openai", "llama_cpp", "mock")

# Errors that retrying cannot fix: bad input or missing configuration.
NOT_RETRIED = (ValueError, TypeError, FileNotFoundError, ImportError)


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
        retries=None,
        retry_delay=1.0,
    ):
        """Create a client.

        ``retries`` is how many times to retry a failed call (default 0, or the
        ``NATLAS_RETRIES`` environment variable). Retries wait ``retry_delay``
        seconds, doubling each time, and only apply to runtime failures such as
        a sleeping Space or a dropped connection, not to invalid input.
        """

        self.retries = max(0, int(
            retries if retries is not None else os.getenv("NATLAS_RETRIES", 0)
        ))
        self.retry_delay = retry_delay
        self.runtime = runtime or self._create_runtime(
            runtime_type=runtime_type,
            base_url=base_url,
            api_key=api_key,
            model=model,
            model_path=model_path,
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
        )

    def _call(self, function, *args, **kwargs):
        delay = self.retry_delay

        for attempt in range(self.retries + 1):
            try:
                return function(*args, **kwargs)
            except NOT_RETRIED:
                raise
            except Exception:
                if attempt == self.retries:
                    raise

                time.sleep(delay)
                delay *= 2

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

        # Runtimes are imported on demand so that using one backend does not
        # require the dependencies of the others.
        if runtime_type == "gradio":
            from runtime.gradio import GradioRuntime

            return GradioRuntime(
                base_url=(
                    base_url
                    or os.getenv("NATLAS_GRADIO_BASE_URL")
                )
            )

        if runtime_type == "openai":
            from runtime.openai_compatible import OpenAICompatibleRuntime

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

        if runtime_type == "mock":
            from runtime.mock import MockRuntime

            return MockRuntime()

        raise ValueError(
            f"Unsupported N-ATLaS runtime: {runtime_type}"
        )

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a response from N-ATLaS.

        ``system``, ``temperature`` and ``max_tokens`` are optional. Only the
        options that are set are passed to the runtime, so custom runtimes
        that implement ``generate(prompt)`` keep working.
        """

        options = {
            key: value
            for key, value in (
                ("system", system),
                ("temperature", temperature),
                ("max_tokens", max_tokens),
            )
            if value is not None
        }

        return self._call(self.runtime.generate, prompt, **options)

    def chat(
        self,
        messages: list[dict],
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Continue a conversation and return the assistant's reply.

        ``messages`` is a list of ``{"role": "user" | "assistant", "content": ...}``
        ending with a user message. Leading ``system`` messages are merged
        into ``system``.
        """

        system_parts = [system] if system and system.strip() else []
        turns = []

        for message in messages:
            if (
                not isinstance(message, dict)
                or message.get("role") not in ("system", "user", "assistant")
                or not isinstance(message.get("content"), str)
            ):
                raise ValueError(
                    "Each message needs a role (system, user or assistant) and text content."
                )

            if message["role"] == "system":
                system_parts.append(message["content"])
            else:
                turns.append({"role": message["role"], "content": message["content"]})

        if not turns or turns[-1]["role"] != "user":
            raise ValueError("The last message must be from the user.")

        options = {
            key: value
            for key, value in (
                ("system", "\n\n".join(system_parts) or None),
                ("temperature", temperature),
                ("max_tokens", max_tokens),
            )
            if value is not None
        }

        chat = getattr(self.runtime, "chat", None)

        if chat is not None:
            return self._call(chat, turns, **options)

        # Custom runtimes that only implement generate(prompt).
        from runtime.base import compose_prompt, messages_to_prompt

        text = compose_prompt(messages_to_prompt(turns), options.pop("system", None))

        return self._call(self.runtime.generate, text, **options)

    def conversation(self, system: str | None = None, **options) -> Conversation:
        """Start a multi-turn conversation that remembers its history."""

        return Conversation(self, system=system, **options)
