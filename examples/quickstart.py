"""Minimal N-ATLaS SDK example.

Run from the project root:

    python -m examples.quickstart

Uses the offline mock runtime unless NATLAS_RUNTIME is set, so it works without
a model. Set NATLAS_RUNTIME=gradio (and NATLAS_GRADIO_BASE_URL) for live inference.
"""

import os

from sdk.natlas_sdk import NAtlas

client = NAtlas(runtime_type=os.getenv("NATLAS_RUNTIME", "mock"))

print(
    client.generate(
        "Translate into Hausa: Good morning, how are you?",
        system="Reply with the translation only.",
        temperature=0.2,
        max_tokens=100,
    )
)
