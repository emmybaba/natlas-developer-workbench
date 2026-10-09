from fastapi.testclient import TestClient

from playground.app import app


client = TestClient(app)


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
    assert "N-ATLaS Developer Playground" in response.text


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


if __name__ == "__main__":
    test_health_endpoint()
    test_playground_serves_html()
    test_empty_prompt_is_rejected()
    print("Playground tests passed.")