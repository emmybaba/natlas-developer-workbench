import pytest
from fastapi.testclient import TestClient

from playground.app import app, clear_clients


client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_clients():
    clear_clients()
    yield
    clear_clients()


def test_health_endpoint():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "N-ATLaS Developer Workbench",
    }


def test_playground_serves_html():
    response = client.get("/")

    assert response.status_code == 200
    assert "N-ATLaS Developer Workbench" in response.text


def test_empty_prompt_is_rejected():
    response = client.post(
        "/api/generate",
        json={"prompt": "   "},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Prompt must not be empty."


def test_inference_failure_returns_json_error(monkeypatch):
    def fail_to_initialize():
        raise ValueError("Test runtime configuration failure")

    monkeypatch.setattr(
        "playground.app.NAtlas",
        fail_to_initialize,
    )

    response = client.post(
        "/api/generate",
        json={"prompt": "Explain antimicrobial resistance."},
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": (
            "Inference failed. Check the runtime configuration "
            "and inference service availability."
        )
    }


def test_runtimes_endpoint_lists_mock_as_configured():
    response = client.get("/api/runtimes")

    assert response.status_code == 200
    by_id = {item["id"]: item for item in response.json()["runtimes"]}
    assert set(by_id) == {"gradio", "openai", "llama_cpp", "mock"}
    assert by_id["mock"]["configured"] is True


def test_generate_with_mock_runtime_returns_metadata():
    response = client.post(
        "/api/generate",
        json={"prompt": "Bawo ni", "runtime": "mock", "temperature": 0.3},
    )

    body = response.json()
    assert response.status_code == 200
    assert "Echo: Bawo ni" in body["response"]
    assert body["runtime"] == "mock"
    assert isinstance(body["latency_ms"], int)


def test_unknown_runtime_and_bad_options_are_rejected():
    unknown = client.post("/api/generate", json={"prompt": "x", "runtime": "nope"})
    hot = client.post("/api/generate", json={"prompt": "x", "temperature": 9})

    assert unknown.status_code == 422
    assert hot.status_code == 422


def test_compare_reports_each_runtime_outcome(monkeypatch):
    monkeypatch.delenv("NATLAS_MODEL_PATH", raising=False)

    response = client.post(
        "/api/compare",
        json={"prompt": "hi", "runtimes": ["mock", "llama_cpp"]},
    )

    results = {item["runtime"]: item for item in response.json()["results"]}
    assert response.status_code == 200
    assert results["mock"]["ok"] is True
    assert results["llama_cpp"]["ok"] is False


def test_compare_requires_two_distinct_runtimes():
    assert client.post("/api/compare", json={"prompt": "x", "runtimes": ["mock"]}).status_code == 422
    assert client.post("/api/compare", json={"prompt": "x", "runtimes": ["mock", "mock"]}).status_code == 422


def test_datasets_and_single_case_evaluation():
    listing = client.get("/api/datasets").json()["datasets"]
    names = {item["name"] for item in listing}
    assert {"smoke", "nigerian-languages"} <= names

    cases = client.get("/api/datasets/smoke").json()["cases"]
    result = client.post(
        "/api/evaluate/case",
        json={"dataset": "smoke", "case_id": cases[0]["id"], "runtime": "mock"},
    ).json()

    assert result["passed"] is True
    assert result["id"] == cases[0]["id"]


def test_dataset_lookup_cannot_escape_the_dataset_directory():
    assert client.get("/api/datasets/..%2FREADME").status_code == 404
    assert client.get("/api/datasets/missing").status_code == 404


def test_chat_endpoint_sends_history_and_validates_last_turn():
    ok = client.post(
        "/api/chat",
        json={
            "runtime": "mock",
            "messages": [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello"},
                {"role": "user", "content": "Again"},
            ],
        },
    )
    bad = client.post(
        "/api/chat",
        json={"runtime": "mock", "messages": [{"role": "assistant", "content": "x"}]},
    )

    assert ok.status_code == 200
    assert "(turn 2)" in ok.json()["response"]
    assert bad.status_code == 422


@pytest.fixture
def apps_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("playground.app.APPS_DIR", tmp_path)
    return tmp_path


def test_app_save_list_run_delete_cycle(apps_dir):
    spec = {"name": "greeter", "template": "Greet {{person}}."}

    saved = client.post("/api/apps", json={"spec": spec})
    assert saved.status_code == 200
    assert saved.json()["variables"] == ["person"]
    assert (apps_dir / "greeter.json").is_file()

    listed = client.get("/api/apps").json()["apps"]
    assert [item["name"] for item in listed] == ["greeter"]

    run = client.post("/api/apps/greeter/run", json={"runtime": "mock", "inputs": {"person": "Ade"}})
    assert run.status_code == 200
    assert "Greet Ade." in run.json()["output"]

    missing = client.post("/api/apps/greeter/run", json={"runtime": "mock", "inputs": {}})
    assert missing.status_code == 422

    assert client.delete("/api/apps/greeter").status_code == 200
    assert client.get("/api/apps/greeter").status_code == 404


def test_app_names_cannot_escape_the_apps_directory(apps_dir):
    assert client.post("/api/apps", json={"spec": {"name": "../evil", "template": "x"}}).status_code == 422
    assert client.get("/api/apps/..%2Fsecret").status_code == 404
    assert client.delete("/api/apps/..%2Fsecret").status_code == 404
    assert list(apps_dir.iterdir()) == []


def test_app_test_endpoint_reports_unusable_json_with_raw_reply(apps_dir):
    spec = {
        "name": "extract",
        "template": "Extract from {{m}}",
        "output": {"type": "json", "keys": ["never_present"]},
    }

    body = client.post(
        "/api/apps/test",
        json={"spec": spec, "inputs": {"m": "x"}, "runtime": "mock"},
    ).json()

    assert body["ok"] is False
    assert body["kind"] == "output"
    assert body["raw"]


def test_app_render_does_not_call_a_model(apps_dir):
    body = client.post(
        "/api/apps/render",
        json={"spec": {"name": "x1", "template": "Say {{w}}"}, "inputs": {"w": "hi"}},
    ).json()

    assert body["prompt"] == "Say hi"


def test_gateway_chat_completion_has_openai_shape():
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "natlas-mock",
            "messages": [
                {"role": "system", "content": "Be brief"},
                {"role": "user", "content": "Bawo ni"},
            ],
            "temperature": 0.2,
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["object"] == "chat.completion"
    assert body["model"] == "natlas-mock"
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert "Bawo ni" in body["choices"][0]["message"]["content"]
    assert body["x_natlas"]["runtime"] == "mock"


def test_gateway_rejects_streaming_and_bad_last_turn():
    stream = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "x"}], "stream": True},
    )
    last = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "assistant", "content": "x"}]},
    )

    assert stream.status_code == 400
    assert stream.json()["error"]["type"] == "invalid_request_error"
    assert last.status_code == 400


def test_gateway_failure_is_an_openai_style_502(monkeypatch):
    monkeypatch.delenv("NATLAS_MODEL_PATH", raising=False)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "natlas-llama_cpp",
            "messages": [{"role": "user", "content": "x"}],
        },
    )

    assert response.status_code == 502
    assert response.json()["error"]["type"] == "api_error"


def test_gateway_models_lists_configured_runtimes():
    ids = [m["id"] for m in client.get("/v1/models").json()["data"]]

    assert "natlas" in ids
    assert "natlas-mock" in ids


def test_gateway_key_is_enforced_when_set(monkeypatch):
    monkeypatch.setenv("NATLAS_GATEWAY_KEY", "s3cret")

    assert client.get("/v1/models").status_code == 401
    assert client.get("/v1/models", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get("/v1/models", headers={"Authorization": "Bearer s3cret"}).status_code == 200


if __name__ == "__main__":
    test_health_endpoint()
    test_playground_serves_html()
    test_empty_prompt_is_rejected()
    print("Playground tests passed.")