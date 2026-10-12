class Conversation:
    """A multi-turn conversation that keeps its own history.

    Create one with ``NAtlas.conversation()``::

        chat = client.conversation(system="Answer briefly.")
        chat.say("Hello")
        chat.say("And in Yoruba?")
    """

    def __init__(self, client, system=None, max_messages=40, **options):
        self.client = client
        self.system = system
        self.max_messages = max_messages
        self.options = options
        self.history: list[dict] = []

    def say(self, text: str, **options) -> str:
        """Add a user message, get the reply, and record both.

        If the call fails, the history is left as it was.
        """

        if not isinstance(text, str) or not text.strip():
            raise ValueError("Message must not be empty.")

        pending = self.history + [{"role": "user", "content": text}]
        window = pending[-self.max_messages:]

        # Never start the window on an assistant message.
        while window and window[0]["role"] != "user":
            window = window[1:]

        reply = self.client.chat(
            window, system=self.system, **{**self.options, **options}
        )

        self.history = pending + [{"role": "assistant", "content": reply}]

        return reply

    def reset(self) -> None:
        self.history = []
