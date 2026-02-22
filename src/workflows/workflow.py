from abc import ABC, abstractmethod
from typing import Dict


class Workflow(ABC):
    @abstractmethod
    def run(self, input: Dict) -> Dict | str | None:
        pass
