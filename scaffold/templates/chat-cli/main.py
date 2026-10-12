"""{{project_name}}: a terminal chat with N-ATLaS that remembers the conversation."""

import os

from natlas_sdk import NAtlas

SYSTEM = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant. Keep answers short.")


def main() -> None:
    runtime = os.getenv("NATLAS_RUNTIME", "mock")

    if runtime == "mock":
        print("Using the offline mock runtime (it only echoes). "
              "Set NATLAS_RUNTIME=gradio and NATLAS_GRADIO_BASE_URL for a real model.\n")

    # retries=2 re-tries transient failures such as a sleeping Space.
    client = NAtlas(runtime_type=runtime, retries=2)
    chat = client.conversation(system=SYSTEM)

    print("Type a message. /reset clears the history, /quit exits.")

    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not text:
            continue
        if text == "/quit":
            break
        if text == "/reset":
            chat.reset()
            print("(history cleared)")
            continue

        try:
            print("natlas>", chat.say(text))
        except Exception as error:  # keep the loop alive on a failed call
            print(f"error: {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
