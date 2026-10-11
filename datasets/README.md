# Prompt suites

JSONL files in `datasets/prompts/` are prompt suites. Each line is one case:

```json
{"id": "ha-question", "prompt": "Menene babban birnin Najeriya?", "tags": ["hausa"], "expect_any": ["Abuja"]}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `prompt` | string, required | The user prompt |
| `id` | string | Unique name for the case (defaults to file and line) |
| `system` | string | System instruction for this case |
| `tags` | list of strings | Free-form labels |
| `expect_contains` | list of strings | Every string must appear (case-insensitive) |
| `expect_any` | list of strings | At least one string must appear |
| `expect_not_contains` | list of strings | None of the strings may appear |
| `max_chars` | integer | Maximum response length |
| `expect_json` | boolean | The whole response must parse as JSON |

Every case also requires a non-empty response.

These checks are simple assertions. They do **not** score translation quality,
fluency or factual accuracy. Cases without `expect_*` fields only confirm that
the runtime responds, and record latency, so a human can read the output.
Add expectations only where you can state them with confidence.

The bundled suites are starting points written for this project, not a
benchmark. Review the prompts (especially the non-English ones) with a fluent
speaker before relying on them.

Run a suite from the command line:

```bash
python -m evaluation datasets/prompts/smoke.jsonl --runtime mock
python -m evaluation datasets/prompts/nigerian-languages.jsonl --runtime gradio --out report.json
```

The process exits with status 1 if any case fails or errors.
