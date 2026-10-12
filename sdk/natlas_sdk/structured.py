"""Helpers for getting structured (JSON) output from a text model.

Language models often wrap JSON in prose or code fences, or add a trailing
sentence. ``extract_json`` copes with that. ``generate_json`` adds validation
of required keys and a bounded number of corrective retries. Nothing here can
guarantee the model returns what you asked for, so callers should handle
``OutputError``.
"""

import json
import re

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


class OutputError(ValueError):
    """The model's output did not match the expected structure."""

    def __init__(self, message: str, raw: str = ""):
        super().__init__(message)
        self.raw = raw


def extract_json(text: str):
    """Return the first JSON object or array found in ``text``.

    Raises ``OutputError`` if there is none.
    """

    candidates = [text]
    candidates[:0] = [m.strip() for m in FENCE.findall(text)]
    decoder = json.JSONDecoder()

    for candidate in candidates:
        for match in re.finditer(r"[{\[]", candidate):
            try:
                value, _ = decoder.raw_decode(candidate[match.start():])
            except ValueError:
                continue
            return value

    raise OutputError("No valid JSON object or array found in the response.", text)


def check_keys(value, keys) -> None:
    """Require ``value`` to be an object containing every key in ``keys``."""

    if not keys:
        return

    if not isinstance(value, dict):
        raise OutputError("Expected a JSON object.")

    missing = [key for key in keys if key not in value]

    if missing:
        raise OutputError("JSON is missing key(s): " + ", ".join(missing))


def generate_json(client, prompt, keys=(), retries=1, system=None, **options):
    """Ask the model for JSON and validate it.

    On a parse or key failure the model is shown its own reply and asked to
    try again, up to ``retries`` extra times. Returns ``(value, raw, attempts)``.
    """

    messages = [{"role": "user", "content": prompt}]
    raw = ""
    reason = ""

    for attempt in range(1, retries + 2):
        raw = client.chat(messages, system=system, **options)

        try:
            value = extract_json(raw)
            check_keys(value, keys)
            return value, raw, attempt
        except OutputError as error:
            reason = str(error)

        messages = messages + [
            {"role": "assistant", "content": raw},
            {
                "role": "user",
                "content": (
                    f"That reply was not usable: {reason} "
                    "Reply again with only the JSON, no other text."
                ),
            },
        ]

    raise OutputError(reason, raw)
