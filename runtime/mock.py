import json
import re
import time

from .base import NAtlasRuntime


class MockRuntime(NAtlasRuntime):
    """Offline runtime for developing against the workbench without a model.

    It does not perform inference. It returns a deterministic reply that
    echoes the prompt and the options it received, which makes it useful for
    exercising the playground, the evaluation runner and application code
    when no real N-ATLaS service is reachable.

    If the prompt or system instruction mentions JSON, it returns a JSON
    object instead, with placeholder values for any keys listed after
    "keys:" in the prompt, so structured-output code paths can be exercised.
    """

    def __init__(self, delay: float = 0.0):
        self.delay = delay

    def chat(self, messages: list[dict], **options) -> str:
        turns = sum(1 for m in messages if m["role"] == "user")

        context = "\n".join(m["content"] for m in messages if m["role"] == "user")

        return self._reply(
            messages[-1]["content"], options, f"(turn {turns})", context
        )

    def generate(self, prompt: str, **options) -> str:
        return self._reply(prompt, options)

    def _reply(self, prompt: str, options: dict, note: str = "", context: str | None = None) -> str:
        if self.delay:
            time.sleep(self.delay)

        context = prompt if context is None else context

        if "json" in (context + str(options.get("system") or "")).lower():
            return json.dumps(self._json_reply(context))

        lines = [f"[mock runtime] Echo: {prompt}" + (f" {note}" if note else "")]

        used = {k: v for k, v in options.items() if v not in (None, "")}

        if used:
            rendered = ", ".join(f"{k}={v!r}" for k, v in sorted(used.items()))
            lines.append(f"[options] {rendered}")

        return "\n".join(lines)

    @staticmethod
    def _json_reply(prompt: str) -> dict:
        match = re.search(r"keys?\b[^:\n]{0,40}:\s*([A-Za-z_][\w ,]*)", prompt)
        keys = [k.strip() for k in match.group(1).split(",")] if match else []
        keys = [k for k in keys if re.fullmatch(r"[A-Za-z_]\w*", k)]

        if not keys:
            return {"mock": True, "echo": prompt}

        return {key: f"mock-{key}" for key in keys}
