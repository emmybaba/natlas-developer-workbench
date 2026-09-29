from runtime.base import NAtlasRuntime


class MockRuntime(NAtlasRuntime):
    """Test runtime used without requiring a live N-ATLaS server."""

    def generate(self, prompt: str) -> str:
        return f"Mock response: {prompt}"


def test_runtime_contract():
    runtime = MockRuntime()

    result = runtime.generate("Hello N-ATLaS")

    assert result == "Mock response: Hello N-ATLaS"


if __name__ == "__main__":
    test_runtime_contract()
    print("Runtime contract test passed.")
