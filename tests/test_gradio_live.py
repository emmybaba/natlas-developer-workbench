import os

import pytest

from runtime.gradio import GradioRuntime


@pytest.mark.skipif(
    not os.getenv("NATLAS_GRADIO_BASE_URL"),
    reason="NATLAS_GRADIO_BASE_URL is not configured.",
)
def test_live_gradio_inference():
    runtime = GradioRuntime(
        base_url=os.getenv("NATLAS_GRADIO_BASE_URL"),
        temperature=0.2,
        max_tokens=100,
    )

    response = runtime.generate(
        "In one sentence, explain why developer SDKs are useful for AI models."
    )

    assert isinstance(response, str)
    assert response.strip(), "The runtime returned an empty response."

    print("\nN-ATLaS response:")
    print(response)
