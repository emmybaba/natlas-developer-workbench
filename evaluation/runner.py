"""Prompt-suite evaluation for N-ATLaS runtimes.

A suite is a JSONL file with one case per line. See ``datasets/README.md``
for the case format. The checks here are simple, deterministic assertions
about a response (presence of text, substrings, length, valid JSON). They do
not measure translation quality, factual accuracy or fluency.
"""

import json
import time
from pathlib import Path

CASE_FIELDS = (
    "id",
    "prompt",
    "system",
    "tags",
    "expect_contains",
    "expect_any",
    "expect_not_contains",
    "max_chars",
    "expect_json",
)


def load_cases(path) -> list[dict]:
    """Load and validate cases from a JSONL file."""

    path = Path(path)
    cases = []
    seen = set()

    with path.open(encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                case = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"{path.name}:{number}: invalid JSON ({error.msg})"
                ) from None

            cases.append(validate_case(case, f"{path.name}:{number}", seen))

    return cases


def validate_case(case, where: str = "case", seen: set | None = None) -> dict:
    """Validate one case and return a normalised copy."""

    if not isinstance(case, dict):
        raise ValueError(f"{where}: a case must be a JSON object")

    unknown = set(case) - set(CASE_FIELDS)

    if unknown:
        raise ValueError(
            f"{where}: unknown field(s): {', '.join(sorted(unknown))}"
        )

    prompt = case.get("prompt")

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(f"{where}: 'prompt' must be a non-empty string")

    case_id = str(case.get("id") or where)

    if seen is not None:
        if case_id in seen:
            raise ValueError(f"{where}: duplicate id {case_id!r}")
        seen.add(case_id)

    for field in ("expect_contains", "expect_any", "expect_not_contains", "tags"):
        value = case.get(field, [])
        if not isinstance(value, list) or not all(
            isinstance(item, str) for item in value
        ):
            raise ValueError(f"{where}: '{field}' must be a list of strings")

    max_chars = case.get("max_chars")
    if max_chars is not None and (
        not isinstance(max_chars, int)
        or isinstance(max_chars, bool)
        or max_chars < 1
    ):
        raise ValueError(f"{where}: 'max_chars' must be a positive integer")

    return {**case, "id": case_id, "prompt": prompt}


def check_response(case: dict, text: str) -> list[dict]:
    """Run the case's checks against a response.

    Returns a list of ``{"check", "passed", "detail"}`` dicts. A non-empty
    response is always required.
    """

    checks = []
    lowered = text.lower()

    def add(name, passed, detail=""):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    add("non_empty", text.strip(), "" if text.strip() else "response is empty")

    missing = [
        item for item in case.get("expect_contains", [])
        if item.lower() not in lowered
    ]
    if case.get("expect_contains"):
        add(
            "expect_contains",
            not missing,
            f"missing: {', '.join(missing)}" if missing else "",
        )

    if case.get("expect_any"):
        add(
            "expect_any",
            any(item.lower() in lowered for item in case["expect_any"]),
            "none of: " + ", ".join(case["expect_any"]),
        )

    present = [
        item for item in case.get("expect_not_contains", [])
        if item.lower() in lowered
    ]
    if case.get("expect_not_contains"):
        add(
            "expect_not_contains",
            not present,
            f"found: {', '.join(present)}" if present else "",
        )

    if case.get("max_chars") is not None:
        add(
            "max_chars",
            len(text) <= case["max_chars"],
            f"{len(text)} > {case['max_chars']}" if len(text) > case["max_chars"] else "",
        )

    if case.get("expect_json"):
        try:
            json.loads(text)
            add("expect_json", True)
        except ValueError:
            add("expect_json", False, "response is not valid JSON")

    return checks


def run_case(case: dict, generate, **options) -> dict:
    """Run one case.

    ``generate`` is a callable ``generate(prompt, **options) -> str``. A case's
    own ``system`` value overrides one passed in ``options``.
    """

    case = validate_case(case)
    call_options = dict(options)

    if case.get("system"):
        call_options["system"] = case["system"]

    result = {
        "id": case["id"],
        "prompt": case["prompt"],
        "tags": case.get("tags", []),
        "response": None,
        "error": None,
        "latency_ms": None,
        "checks": [],
        "passed": False,
    }

    start = time.perf_counter()

    try:
        text = generate(case["prompt"], **call_options)
    except Exception as error:  # a failing case must not stop the suite
        result["latency_ms"] = round((time.perf_counter() - start) * 1000)
        result["error"] = _describe_error(error)
        return result

    result["latency_ms"] = round((time.perf_counter() - start) * 1000)
    result["response"] = text if isinstance(text, str) else str(text)
    result["checks"] = check_response(case, result["response"])
    result["passed"] = all(check["passed"] for check in result["checks"])

    return result


def summarize(results: list[dict]) -> dict:
    """Aggregate per-case results."""

    total = len(results)
    errors = sum(1 for r in results if r["error"])
    passed = sum(1 for r in results if r["passed"])
    latencies = sorted(r["latency_ms"] for r in results if r["latency_ms"] is not None)

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed - errors,
        "errors": errors,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "latency_ms_avg": round(sum(latencies) / len(latencies)) if latencies else None,
        "latency_ms_max": latencies[-1] if latencies else None,
    }


def run_suite(cases: list[dict], generate, on_result=None, **options) -> dict:
    """Run every case in order and return ``{"summary", "results"}``."""

    results = []

    for case in cases:
        result = run_case(case, generate, **options)
        results.append(result)

        if on_result:
            on_result(result)

    return {"summary": summarize(results), "results": results}


def _describe_error(error: Exception) -> str:
    if isinstance(error, (ValueError, FileNotFoundError, ImportError)):
        return f"{type(error).__name__}: {error}"

    return type(error).__name__
