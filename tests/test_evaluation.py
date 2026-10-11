import json

import pytest

from evaluation.runner import (
    check_response,
    load_cases,
    run_case,
    run_suite,
    summarize,
    validate_case,
)


def echo(prompt, **options):
    return f"echo: {prompt}"


def test_check_response_passes_and_fails():
    case = validate_case(
        {
            "prompt": "x",
            "expect_contains": ["Abuja"],
            "expect_not_contains": ["Lagos"],
            "max_chars": 20,
        }
    )

    assert all(c["passed"] for c in check_response(case, "ABUJA"))

    failed = {c["check"] for c in check_response(case, "Lagos is big and long") if not c["passed"]}
    assert failed == {"expect_contains", "expect_not_contains", "max_chars"}


def test_expect_any_and_json():
    case = validate_case({"prompt": "x", "expect_any": ["a", "b"], "expect_json": True})

    assert all(c["passed"] for c in check_response(case, '{"a": 1}'))

    checks = {c["check"]: c["passed"] for c in check_response(case, "zzz")}
    assert checks["expect_any"] is False
    assert checks["expect_json"] is False


def test_empty_response_fails_non_empty_check():
    result = run_case({"prompt": "x"}, lambda prompt, **o: "   ")

    assert result["passed"] is False
    assert result["checks"][0]["check"] == "non_empty"


def test_generation_error_is_captured_not_raised():
    def broken(prompt, **options):
        raise RuntimeError("secret endpoint details")

    result = run_case({"id": "c1", "prompt": "x"}, broken)

    assert result["error"] == "RuntimeError"
    assert "secret" not in result["error"]
    assert result["passed"] is False


def test_case_system_overrides_default_option():
    seen = {}

    def capture(prompt, **options):
        seen.update(options)
        return "ok"

    run_case({"prompt": "x", "system": "case"}, capture, system="default", temperature=0.3)

    assert seen == {"system": "case", "temperature": 0.3}


def test_suite_summary():
    cases = [
        {"id": "a", "prompt": "hello"},
        {"id": "b", "prompt": "hello", "expect_contains": ["nope"]},
    ]
    report = run_suite(cases, echo)

    assert report["summary"]["total"] == 2
    assert report["summary"]["passed"] == 1
    assert report["summary"]["failed"] == 1
    assert report["summary"]["errors"] == 0
    assert summarize([])["pass_rate"] == 0.0


def test_validation_rejects_bad_cases():
    for bad in (
        {"prompt": ""},
        {"prompt": "x", "bogus": 1},
        {"prompt": "x", "expect_contains": "abc"},
        {"prompt": "x", "max_chars": 0},
        ["not", "an", "object"],
    ):
        with pytest.raises(ValueError):
            validate_case(bad)


def test_load_cases_reports_line_numbers(tmp_path):
    path = tmp_path / "suite.jsonl"
    path.write_text('{"prompt": "ok"}\n\n{broken\n', encoding="utf-8")

    with pytest.raises(ValueError, match=r"suite\.jsonl:3"):
        load_cases(path)


def test_load_cases_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "suite.jsonl"
    path.write_text('{"id": "a", "prompt": "x"}\n{"id": "a", "prompt": "y"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        load_cases(path)


def test_bundled_suites_are_valid():
    from pathlib import Path

    files = sorted(Path(__file__).resolve().parent.parent.glob("datasets/prompts/*.jsonl"))

    assert files
    for path in files:
        assert load_cases(path)
