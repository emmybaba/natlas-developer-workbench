"""Command-line runner: ``python -m evaluation <suite.jsonl> --runtime mock``."""

import argparse
import json
import sys
from pathlib import Path

from evaluation.runner import load_cases, run_suite
from sdk.natlas_sdk import NAtlas


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m evaluation",
        description="Run a JSONL prompt suite against an N-ATLaS runtime.",
    )
    parser.add_argument("suite", help="path to a .jsonl prompt suite")
    parser.add_argument(
        "--runtime",
        help="gradio, openai, llama_cpp or mock (default: NATLAS_RUNTIME or gradio)",
    )
    parser.add_argument("--system", help="system instruction for every case")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--max-tokens", type=int, dest="max_tokens")
    parser.add_argument("--out", help="write the full JSON report to this path")
    args = parser.parse_args(argv)

    try:
        cases = load_cases(args.suite)
        client = NAtlas(runtime_type=args.runtime)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    def show(result):
        if result["error"]:
            status = "ERROR"
        else:
            status = "PASS" if result["passed"] else "FAIL"
        print(f"{status:5} {result['id']}  ({result['latency_ms']} ms)", flush=True)

        for check in result["checks"]:
            if not check["passed"]:
                print(f"        - {check['check']}: {check['detail']}")

        if result["error"]:
            print(f"        - {result['error']}")

    report = run_suite(
        cases,
        client.generate,
        on_result=show,
        system=args.system,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )

    summary = report["summary"]
    print(
        f"\n{summary['passed']}/{summary['total']} passed, "
        f"{summary['failed']} failed, {summary['errors']} errors "
        f"(avg {summary['latency_ms_avg']} ms)"
    )

    if args.out:
        Path(args.out).write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Report written to {args.out}")

    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
