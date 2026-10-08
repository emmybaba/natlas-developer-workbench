from sdk.natlas_sdk import NAtlas
from adapter.natlas.config import NAtlasConfig


class MockRuntime:
    def generate(self, prompt: str) -> str:
        return f"Mock response: {prompt}"


def test_sdk_configuration_requires_endpoint():
    config = NAtlasConfig()

    try:
        config.validate()
    except ValueError as error:
        assert "NATLAS_BASE_URL" in str(error)
    else:
        raise AssertionError(
            "Configuration should require NATLAS_BASE_URL"
        )


def test_sdk_accepts_custom_runtime():
    runtime = MockRuntime()

    client = NAtlas(runtime=runtime)

    result = client.generate("Hello N-ATLaS")

    assert result == "Mock response: Hello N-ATLaS"


if __name__ == "__main__":
    test_sdk_configuration_requires_endpoint()
    test_sdk_accepts_custom_runtime()
    print("SDK tests passed.")