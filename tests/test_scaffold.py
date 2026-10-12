import json

import pytest

from scaffold.cli import available, create, main


def test_all_templates_are_listed():
    assert {"chat-cli", "api-service", "node-client"} <= set(available())


def test_create_substitutes_the_project_name(tmp_path):
    target = tmp_path / "demo"

    files = create("chat-cli", target, "Demo App")

    assert (target / "main.py") in files
    text = (target / "main.py").read_text(encoding="utf-8")
    assert "Demo App" in text
    assert "{{project_name}}" not in text


def test_every_template_renders_without_leftover_placeholders(tmp_path):
    for name in available():
        target = tmp_path / name
        for path in create(name, target, "demo"):
            assert "{{project_name}}" not in path.read_text(encoding="utf-8")


def test_api_service_apps_are_valid_prompt_apps(tmp_path):
    from sdk.natlas_sdk import load_apps

    create("api-service", tmp_path / "svc", "svc")
    loaded = load_apps(tmp_path / "svc" / "apps")

    assert loaded["problems"] == {}
    assert {"translator", "summarizer", "contact-extractor"} <= set(loaded["apps"])


def test_node_client_package_is_valid_json(tmp_path):
    create("node-client", tmp_path / "n", "n")

    assert json.loads((tmp_path / "n" / "package.json").read_text())["type"] == "module"


def test_refuses_unknown_template_bad_name_and_non_empty_directory(tmp_path):
    with pytest.raises(ValueError, match="Unknown template"):
        create("nope", tmp_path / "a")

    with pytest.raises(ValueError, match="Project name"):
        create("chat-cli", tmp_path / "b", "bad{{name}}")

    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "keep.txt").write_text("x")

    with pytest.raises(ValueError, match="not empty"):
        create("chat-cli", tmp_path / "c", "c")


def test_cli_exit_codes(tmp_path, capsys):
    assert main(["templates"]) == 0
    assert main(["new", "chat-cli", str(tmp_path / "ok")]) == 0
    assert main(["new", "chat-cli", str(tmp_path / "ok")]) == 2
    assert main(["new", "nope", str(tmp_path / "x")]) == 2
