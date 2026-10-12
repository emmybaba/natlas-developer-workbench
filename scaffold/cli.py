"""Create a starter project: ``natlas new chat-cli my-chat``."""

import argparse
import re
import sys
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
DESCRIPTIONS = {
    "chat-cli": "Terminal chat with memory (Python, uses the SDK)",
    "api-service": "HTTP service exposing your prompt apps (Python, FastAPI)",
    "node-client": "Node.js script that calls the workbench's OpenAI-compatible gateway",
}
SKIP = {"__pycache__", ".DS_Store"}


def available() -> list[str]:
    return sorted(p.name for p in TEMPLATES_DIR.iterdir() if p.is_dir())


def create(template: str, target, project_name: str | None = None) -> list[Path]:
    """Copy ``template`` into ``target`` and return the files written."""

    if template not in available():
        raise ValueError(
            f"Unknown template '{template}'. Available: {', '.join(available())}"
        )

    target = Path(target)
    name = (project_name or target.resolve().name).strip()

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]{0,60}", name):
        raise ValueError(
            "Project name must be 1-61 characters: letters, digits, spaces, "
            "dots, dashes or underscores."
        )

    if target.exists() and any(target.iterdir()):
        raise ValueError(f"{target} already exists and is not empty.")

    written = []
    source = TEMPLATES_DIR / template

    for path in sorted(source.rglob("*")):
        if path.is_dir() or SKIP & set(path.parts):
            continue

        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            path.read_text(encoding="utf-8").replace("{{project_name}}", name),
            encoding="utf-8",
        )
        written.append(destination)

    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="natlas", description="N-ATLaS Developer Workbench project tools."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("templates", help="list starter templates")

    new = commands.add_parser("new", help="create a project from a template")
    new.add_argument("template")
    new.add_argument("directory")
    new.add_argument("--name", help="project name (default: the directory name)")

    args = parser.parse_args(argv)

    if args.command == "templates":
        for name in available():
            print(f"{name:14} {DESCRIPTIONS.get(name, '')}")
        return 0

    try:
        files = create(args.template, args.directory, args.name)
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(f"Created {args.directory} from '{args.template}':")
    for path in files:
        print("  " + str(path.relative_to(args.directory)))
    print(f"\nNext: see {Path(args.directory) / 'README.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
