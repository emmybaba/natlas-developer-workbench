from abc import ABC, abstractmethod


def compose_prompt(prompt: str, system: str | None = None) -> str:
    """Fold an optional system instruction into a single prompt string.

    Used by runtimes whose backend has no verified system-role support.
    """

    system = (system or "").strip()

    if not system:
        return prompt

    return f"{system}\n\n{prompt}"


def messages_to_prompt(messages: list[dict]) -> str:
    """Flatten a conversation into one prompt for single-prompt backends."""

    lines = []

    for message in messages:
        speaker = "User" if message["role"] == "user" else "Assistant"
        lines.append(f"{speaker}: {message['content']}")

    lines.append("Assistant:")

    return "\n".join(lines)


ROLES = ("system", "user", "assistant")


def validate_messages(messages) -> list[dict]:
    """Validate and normalise a chat message list."""

    if not isinstance(messages, (list, tuple)) or not messages:
        raise ValueError("messages must be a non-empty list.")

    cleaned = []

    for item in messages:
        if (
            not isinstance(item, dict)
            or item.get("role") not in ROLES
            or not isinstance(item.get("content"), str)
        ):
            raise ValueError(
                "Each message needs a role (system, user or assistant) "
                "and a string content."
            )

        cleaned.append({"role": item["role"], "content": item["content"]})

    if cleaned[-1]["role"] != "user":
        raise ValueError("The last message must have the role 'user'.")

    return cleaned


def merge_system(messages: list[dict], system: str | None = None):
    """Return ``(system_text, conversation)`` with system messages pulled out."""

    parts = [system.strip()] if system and system.strip() else []
    parts += [m["content"].strip() for m in messages if m["role"] == "system"]
    conversation = [m for m in messages if m["role"] != "system"]

    return "\n\n".join(p for p in parts if p), conversation


class NAtlasRuntime(ABC):
    """Abstract interface for an N-ATLaS inference runtime.

    Runtimes may accept these optional per-call keyword options:

    * ``system``: a system instruction
    * ``temperature``: sampling temperature
    * ``max_tokens``: maximum number of tokens to generate

    Options that are not supplied fall back to the runtime's own defaults.
    """

    @abstractmethod
    def generate(self, prompt: str, **options) -> str:
        """Generate a response from N-ATLaS."""
        raise NotImplementedError

    def chat(self, messages: list[dict], **options) -> str:
        """Continue a multi-turn conversation.

        ``messages`` is a list of ``{"role": "user" | "assistant", "content": str}``
        ending with a user message. This default flattens the conversation into
        one prompt; runtimes with real chat support override it.
        """

        system = options.pop("system", None)

        return self.generate(
            compose_prompt(messages_to_prompt(messages), system), **options
        )
