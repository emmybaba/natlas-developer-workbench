"""Command line for prompt apps.

    python -m sdk.natlas_sdk list
    python -m sdk.natlas_sdk run translator -i text="Good morning" -i target_language=Yoruba
    python -m sdk.natlas_sdk run apps/translator.json --runtime mock --show-prompt
"""

import argparse
import json
import sys
from pathlib import Path

from .apps import AppError, PromptApp, load_apps
from .client import NAtlas
from .structured import OutputError

DEFAULT_DIR = Path("apps")


def _resolve(target: str, directory: Path) -> PromptApp:
    path = Path(target)

    if not path.suffix:
        path = directory / f"{target}.json"

    if not path.exists():
        raise AppError(f"App not found: {target}")

    return PromptApp.from_file(path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m sdk.natlas_sdk")
    parser.add_argument("--apps-dir", default=str(DEFAULT_DIR), help="folder of app JSON files (default: apps)")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="list the available apps")

    run = commands.add_parser("run", help="run an app")
    run.add_argument("app", help="app name or path to an app .json file")
    run.add_argument("-i", "--input", action="append", default=[], metavar="NAME=VALUE")
    run.add_argument("--runtime", help="gradio, openai, llama_cpp or mock")
    run.add_argument("--temperature", type=float)
    run.add_argument("--max-tokens", type=int, dest="max_tokens")
    run.add_argument("--show-prompt", action="store_true", help="print the rendered prompt and stop (no model call)")

    args = parser.parse_args(argv)
    directory = Path(args.apps_dir)

    if args.command == "list":
        loaded = load_apps(directory) if directory.is_dir() else {"apps": {}, "problems": {}}

        for name, app in loaded["apps"].items():
            print(f"{name:24} {app.spec.get('description', '')}  [inputs: {', '.join(app.variables)}]")

        for file, problem in loaded["problems"].items():
            print(f"! {file}: {problem}", file=sys.stderr)

        return 0

    try:
        app = _resolve(args.app, directory)
        inputs = {}

        for item in args.input:
            key, sep, value = item.partition("=")

            if not sep:
                raise AppError(f"Inputs look like NAME=VALUE, got: {item}")

            inputs[key] = value

        if args.show_prompt:
            system, prompt = app.render(inputs)
            print(f"[system]\n{system or '(none)'}\n\n[prompt]\n{prompt}")
            return 0

        client = NAtlas(runtime_type=args.runtime)
        result = app.run(client, inputs, temperature=args.temperature, max_tokens=args.max_tokens)
    except OutputError as error:
        print(f"error: {error}\n--- raw model output ---\n{error.raw}", file=sys.stderr)
        return 1
    except (AppError, ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(result.output if isinstance(result.output, str) else json.dumps(result.output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
