from abc import ABC, abstractmethod


class Page(ABC):
    """Abstract base class for UI pages."""

    @abstractmethod
    def render(self):
        pass
