from abc import ABC, abstractmethod


class NAtlasRuntime(ABC):
    """Abstract interface for an N-ATLaS inference runtime."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a response from N-ATLaS."""
        raise NotImplementedError
