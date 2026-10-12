import os

os.environ["NATLAS_RUNTIME"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402

client = TestClient(app)


def test_health_lists_apps():
    body = client.get("/health").json()

    assert "translator" in body["apps"]
    assert body["problems"] == {}


def test_run_text_app():
    response = client.post(
        "/apps/translator/run", json={"inputs": {"text": "Good morning"}}
    )

    assert response.status_code == 200
    assert response.json()["output"]


def test_missing_input_is_a_422():
    response = client.post("/apps/translator/run", json={"inputs": {}})

    assert response.status_code == 422


def test_unknown_app_is_a_404():
    assert client.post("/apps/nope/run", json={}).status_code == 404
