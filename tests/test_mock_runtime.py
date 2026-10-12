from runtime.mock import MockRuntime
from sdk.natlas_sdk import NAtlas


def test_mock_runtime_echoes_prompt_and_options():
    text = MockRuntime().generate("Bawo", system="Be brief", temperature=0.5)

    assert "Echo: Bawo" in text
    assert "system='Be brief'" in text
    assert "temperature=0.5" in text


def test_sdk_can_create_mock_runtime():
    client = NAtlas(runtime_type="mock")

    assert "Echo: hi" in client.generate("hi")


def test_sdk_only_passes_options_that_are_set():
    calls = []

    class Recorder:
        def generate(self, prompt, **options):
            calls.append(options)
            return "ok"

    client = NAtlas(runtime=Recorder())
    client.generate("a")
    client.generate("b", system="s", max_tokens=5)

    assert calls == [{}, {"system": "s", "max_tokens": 5}]


def test_sdk_rejects_unknown_runtime():
    try:
        NAtlas(runtime_type="nope")
    except ValueError as error:
        assert "Unsupported" in str(error)
    else:
        raise AssertionError("Unknown runtime should be rejected")


def test_sdk_retries_runtime_failures_with_backoff(monkeypatch):
    import sdk.natlas_sdk.client as client_module

    sleeps = []
    monkeypatch.setattr(client_module.time, "sleep", sleeps.append)

    class Flaky:
        calls = 0

        def generate(self, prompt, **options):
            Flaky.calls += 1
            if Flaky.calls < 3:
                raise ConnectionError("down")
            return "ok"

    client = NAtlas(runtime=Flaky(), retries=2, retry_delay=0.5)

    assert client.generate("hi") == "ok"
    assert Flaky.calls == 3
    assert sleeps == [0.5, 1.0]


def test_sdk_gives_up_after_the_last_retry_and_never_retries_bad_input(monkeypatch):
    import sdk.natlas_sdk.client as client_module

    monkeypatch.setattr(client_module.time, "sleep", lambda s: None)
    calls = []

    class Down:
        def generate(self, prompt, **options):
            calls.append(1)
            raise ConnectionError("down")

    try:
        NAtlas(runtime=Down(), retries=1).generate("hi")
    except ConnectionError:
        pass
    else:
        raise AssertionError("should raise after retries are used up")

    assert len(calls) == 2

    class Misconfigured:
        def generate(self, prompt, **options):
            calls.append(1)
            raise ValueError("NATLAS_GRADIO_BASE_URL is not configured.")

    calls.clear()
    try:
        NAtlas(runtime=Misconfigured(), retries=3).generate("hi")
    except ValueError:
        pass

    assert len(calls) == 1
