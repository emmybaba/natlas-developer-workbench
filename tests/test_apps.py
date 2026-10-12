import json

import pytest

from sdk.natlas_sdk import (
    AppError,
    NAtlas,
    OutputError,
    PromptApp,
    extract_json,
    generate_json,
    load_apps,
)


class Scripted:
    """Runtime that replies from a list and records every call."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def generate(self, prompt, **options):
        self.calls.append(("generate", prompt, options))
        return self.replies.pop(0)

    def chat(self, messages, **options):
        self.calls.append(("chat", [dict(m) for m in messages], options))
        return self.replies.pop(0)


SPEC = {
    "name": "greeter",
    "system": "Be brief in {{language}}.",
    "template": "Greet {{person}} in {{language}}.",
    "inputs": [{"name": "language", "default": "Hausa"}],
}


def test_extract_json_handles_prose_and_fences():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('Sure! Here it is: {"a": [1, 2]} Hope that helps.') == {"a": [1, 2]}
    assert extract_json('```json\n{"a": "x"}\n```') == {"a": "x"}
    assert extract_json("Items: [1, 2, 3]") == [1, 2, 3]

    with pytest.raises(OutputError):
        extract_json("no json here {oops")


def test_generate_json_retries_with_the_bad_reply_in_context():
    client = NAtlas(runtime=Scripted("not json", '{"name": "Ade"}'))

    value, raw, attempts = generate_json(client, "Give JSON", keys=["name"], retries=1)

    assert value == {"name": "Ade"}
    assert attempts == 2

    second_call_messages = client.runtime.calls[1][1]
    assert [m["role"] for m in second_call_messages] == ["user", "assistant", "user"]
    assert second_call_messages[1]["content"] == "not json"


def test_generate_json_gives_up_and_keeps_the_raw_reply():
    client = NAtlas(runtime=Scripted('{"x": 1}', '{"x": 2}'))

    with pytest.raises(OutputError, match="missing key") as caught:
        generate_json(client, "Give JSON", keys=["name"], retries=1)

    assert caught.value.raw == '{"x": 2}'


def test_app_renders_defaults_and_system_variables():
    system, prompt = PromptApp(SPEC).render({"person": "Ade"})

    assert prompt == "Greet Ade in Hausa."
    assert system == "Be brief in Hausa."


def test_app_rejects_missing_and_unknown_inputs():
    app = PromptApp(SPEC)

    with pytest.raises(AppError, match="Missing input"):
        app.render({})

    with pytest.raises(AppError, match="Unknown input"):
        app.render({"person": "Ade", "typo": "x"})


def test_values_are_not_expanded_twice():
    app = PromptApp({"name": "echo", "template": "Say: {{a}} / {{b}}"})

    _, prompt = app.render({"a": "{{b}}", "b": "real"})

    assert prompt == "Say: {{b}} / real"


def test_app_validation():
    bad_specs = [
        {"name": "Bad Name", "template": "x"},
        {"name": "ok", "template": "  "},
        {"name": "ok", "template": "x", "surprise": 1},
        {"name": "ok", "template": "x {{a}}", "inputs": [{"name": "zzz"}]},
        {"name": "ok", "template": "x", "output": {"type": "xml"}},
        {"name": "ok", "template": "x", "options": {"temperature": 5}},
        {"name": "ok", "template": "x", "options": {"max_tokens": 0}},
        {"name": "ok", "template": "x", "options": {"retries": 99}},
        "not an object",
    ]

    for spec in bad_specs:
        with pytest.raises(AppError):
            PromptApp(spec)


def test_text_app_run_passes_system_and_options():
    runtime = Scripted("Sannu Ade")
    app = PromptApp({**SPEC, "options": {"temperature": 0.1, "max_tokens": 50}})

    result = app.run(NAtlas(runtime=runtime), {"person": "Ade"}, max_tokens=80)

    assert result.output == "Sannu Ade"
    kind, messages, options = runtime.calls[0]
    assert messages == [{"role": "user", "content": "Greet Ade in Hausa."}]
    assert options == {"system": "Be brief in Hausa.", "temperature": 0.1, "max_tokens": 80}


def test_json_app_returns_parsed_output():
    app = PromptApp(
        {"name": "extract", "template": "Extract from {{msg}}", "output": {"type": "json", "keys": ["name"]}}
    )

    result = app.run(NAtlas(runtime=Scripted('Result: {"name": "Ade"}')), {"msg": "hi"})

    assert result.output == {"name": "Ade"}


def test_load_apps_reports_problems_without_failing(tmp_path):
    (tmp_path / "good.json").write_text(json.dumps({"name": "good", "template": "x"}))
    (tmp_path / "broken.json").write_text("{nope")
    (tmp_path / "mismatch.json").write_text(json.dumps({"name": "other", "template": "x"}))

    loaded = load_apps(tmp_path)

    assert list(loaded["apps"]) == ["good"]
    assert set(loaded["problems"]) == {"broken.json", "mismatch.json"}


def test_bundled_apps_load_cleanly():
    from pathlib import Path

    loaded = load_apps(Path(__file__).resolve().parent.parent / "apps")

    assert loaded["problems"] == {}
    assert {"translator", "summarizer", "contact-extractor"} <= set(loaded["apps"])


def test_conversation_keeps_history_and_survives_failures():
    runtime = Scripted("one", "two")
    chat = NAtlas(runtime=runtime).conversation(system="Brief")

    assert chat.say("a") == "one"
    assert chat.say("b") == "two"
    assert [m["content"] for m in chat.history] == ["a", "one", "b", "two"]
    assert runtime.calls[1][1][-1] == {"role": "user", "content": "b"}
    assert runtime.calls[1][2]["system"] == "Brief"

    runtime.replies = []  # next call raises IndexError
    with pytest.raises(IndexError):
        chat.say("c")

    assert len(chat.history) == 4

    with pytest.raises(ValueError):
        chat.say("   ")


def test_conversation_window_never_starts_on_an_assistant_message():
    runtime = Scripted("1", "2", "3")
    chat = NAtlas(runtime=runtime).conversation(max_messages=3)

    for text in ("a", "b", "c"):
        chat.say(text)

    sent = runtime.calls[2][1]
    assert sent[0]["role"] == "user"


def test_client_chat_validates_and_merges_system_messages():
    runtime = Scripted("ok")
    client = NAtlas(runtime=runtime)

    client.chat(
        [{"role": "system", "content": "S1"}, {"role": "user", "content": "hi"}],
        system="S0",
    )

    _, messages, options = runtime.calls[0]
    assert messages == [{"role": "user", "content": "hi"}]
    assert options["system"] == "S0\n\nS1"

    with pytest.raises(ValueError, match="last message"):
        client.chat([{"role": "assistant", "content": "x"}])

    with pytest.raises(ValueError):
        client.chat([{"role": "robot", "content": "x"}])


def test_client_chat_falls_back_for_generate_only_runtimes():
    class GenerateOnly:
        def generate(self, prompt, **options):
            self.prompt = prompt
            return "ok"

    runtime = GenerateOnly()
    NAtlas(runtime=runtime).chat(
        [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}, {"role": "user", "content": "more"}],
        system="Be brief",
    )

    assert runtime.prompt.startswith("Be brief\n\nUser: hi\nAssistant: yo\nUser: more")
    assert runtime.prompt.endswith("Assistant:")


def test_mock_runtime_json_mode_uses_listed_keys():
    from runtime.mock import MockRuntime

    value = json.loads(MockRuntime().generate("Return JSON. Extract these keys from it: a, b."))

    assert value == {"a": "mock-a", "b": "mock-b"}
