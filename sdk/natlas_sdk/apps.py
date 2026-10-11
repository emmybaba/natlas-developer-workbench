"""Prompt apps: a reusable, shareable definition of one N-ATLaS task.

A prompt app is a small JSON file: a prompt template with ``{{variables}}``,
an optional system instruction, and the output format (plain text or JSON).
The same file can be run from Python, from the command line, or through the
workbench's HTTP API, so an idea tested in the browser becomes application
code without being rewritten.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .structured import OutputError, check_keys, extract_json, generate_json

VARIABLE = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
SPEC_FIELDS = {
    "name", "description", "system", "template", "inputs", "output", "options",
}
MAX_TEXT = 20000


class AppError(ValueError):
    """The app definition or the inputs supplied to it are invalid."""


@dataclass
class AppResult:
    output: object          # str for text apps, parsed JSON for json apps
    raw: str                # the model's raw reply
    attempts: int = 1
    system: str | None = None
    prompt: str = ""


def variables_in(*texts) -> list[str]:
    """Variable names used in the given texts, in first-seen order."""

    seen = []

    for text in texts:
        for name in VARIABLE.findall(text or ""):
            if name not in seen:
                seen.append(name)

    return seen


class PromptApp:
    def __init__(self, spec: dict):
        self.spec = self.validate(spec)

    # ----- construction -----

    @classmethod
    def from_file(cls, path) -> "PromptApp":
        try:
            spec = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as error:
            raise AppError(f"{Path(path).name}: invalid JSON ({error.msg})") from None

        return cls(spec)

    @staticmethod
    def validate(spec) -> dict:
        if not isinstance(spec, dict):
            raise AppError("An app definition must be a JSON object.")

        unknown = set(spec) - SPEC_FIELDS

        if unknown:
            raise AppError("Unknown field(s): " + ", ".join(sorted(unknown)))

        name = spec.get("name")

        if not isinstance(name, str) or not NAME.match(name):
            raise AppError(
                "'name' must be 1-48 characters: lowercase letters, digits "
                "and hyphens, starting with a letter or digit."
            )

        for field in ("description", "system"):
            value = spec.get(field, "")

            if not isinstance(value, str) or len(value) > MAX_TEXT:
                raise AppError(f"'{field}' must be text of at most {MAX_TEXT} characters.")

        template = spec.get("template")

        if not isinstance(template, str) or not template.strip():
            raise AppError("'template' must be a non-empty string.")

        if len(template) > MAX_TEXT:
            raise AppError(f"'template' must be at most {MAX_TEXT} characters.")

        names = variables_in(template, spec.get("system", ""))
        declared = spec.get("inputs", [])

        if not isinstance(declared, list):
            raise AppError("'inputs' must be a list.")

        inputs = []

        for entry in declared:
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                raise AppError("Each input needs a 'name'.")

            if entry["name"] not in names:
                raise AppError(
                    f"Input '{entry['name']}' is not used in the template or system instruction."
                )

            extra = set(entry) - {"name", "label", "default", "required"}

            if extra:
                raise AppError(
                    f"Input '{entry['name']}' has unknown field(s): " + ", ".join(sorted(extra))
                )

            inputs.append(entry)

        output = spec.get("output", {"type": "text"})

        if not isinstance(output, dict) or output.get("type", "text") not in ("text", "json"):
            raise AppError("'output.type' must be 'text' or 'json'.")

        keys = output.get("keys", [])

        if not isinstance(keys, list) or not all(isinstance(k, str) for k in keys):
            raise AppError("'output.keys' must be a list of strings.")

        options = spec.get("options", {})

        if not isinstance(options, dict) or set(options) - {"temperature", "max_tokens", "retries"}:
            raise AppError("'options' may only contain temperature, max_tokens and retries.")

        temperature = options.get("temperature")

        if temperature is not None and (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not 0 <= temperature <= 2
        ):
            raise AppError("'options.temperature' must be a number from 0 to 2.")

        for field, low, high in (("max_tokens", 1, 4096), ("retries", 0, 5)):
            value = options.get(field)

            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high
            ):
                raise AppError(f"'options.{field}' must be an integer from {low} to {high}.")

        return {**spec, "inputs": inputs, "output": {"type": "text", **output}, "options": options}

    # ----- inspection -----

    @property
    def name(self) -> str:
        return self.spec["name"]

    @property
    def variables(self) -> list[str]:
        return variables_in(self.spec["template"], self.spec.get("system", ""))

    @property
    def output_type(self) -> str:
        return self.spec["output"]["type"]

    def _input(self, name: str) -> dict:
        return next((i for i in self.spec["inputs"] if i["name"] == name), {})

    # ----- running -----

    def render(self, inputs: dict | None = None) -> tuple[str | None, str]:
        """Fill in the template. Returns ``(system, prompt)``. Calls no model."""

        inputs = dict(inputs or {})
        unknown = [key for key in inputs if key not in self.variables]

        if unknown:
            raise AppError(
                "Unknown input(s): " + ", ".join(unknown)
                + ". This app expects: " + (", ".join(self.variables) or "no inputs")
            )

        values = {}
        missing = []

        for name in self.variables:
            meta = self._input(name)
            value = inputs.get(name)

            if value is None or str(value).strip() == "":
                if "default" in meta:
                    value = meta["default"]
                elif meta.get("required", True):
                    missing.append(name)
                    continue
                else:
                    value = ""

            values[name] = str(value)

        if missing:
            raise AppError("Missing input(s): " + ", ".join(missing))

        # A single pass, so a value containing "{{x}}" is never expanded again.
        def fill(text):
            return VARIABLE.sub(lambda m: values[m.group(1)], text)

        system = fill(self.spec["system"]).strip() if self.spec.get("system") else None

        return system or None, fill(self.spec["template"])

    def run(self, client, inputs: dict | None = None, **overrides) -> AppResult:
        """Render the app and run it against ``client`` (an ``NAtlas``).

        ``overrides`` may set ``temperature``, ``max_tokens`` or ``retries``.
        Raises ``AppError`` for bad inputs and ``OutputError`` when a JSON app
        gets output it cannot use (the raw reply is on ``error.raw``).
        """

        system, prompt = self.render(inputs)
        options = {**self.spec["options"], **{k: v for k, v in overrides.items() if v is not None}}
        retries = options.pop("retries", 1)

        if self.output_type == "json":
            value, raw, attempts = generate_json(
                client, prompt, keys=self.spec["output"].get("keys", []),
                retries=retries, system=system, **options,
            )
            return AppResult(value, raw, attempts, system, prompt)

        raw = client.chat([{"role": "user", "content": prompt}], system=system, **options)

        return AppResult(raw, raw, 1, system, prompt)


def load_apps(directory) -> dict:
    """Load every ``*.json`` app in a directory. Invalid files are reported, not fatal."""

    apps, problems = {}, {}

    for path in sorted(Path(directory).glob("*.json")):
        try:
            app = PromptApp.from_file(path)

            if app.name != path.stem:
                raise AppError(f"name '{app.name}' must match the file name '{path.stem}'.")

            apps[app.name] = app
        except (AppError, OSError) as error:
            problems[path.name] = str(error)

    return {"apps": apps, "problems": problems}


__all__ = [
    "AppError", "AppResult", "OutputError", "PromptApp", "check_keys",
    "extract_json", "load_apps", "variables_in",
]
