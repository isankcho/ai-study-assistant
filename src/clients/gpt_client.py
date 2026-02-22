from langchain_openai import ChatOpenAI
from config.config import SETTINGS


class GPTClient:
    def __init__(
        self,
        model: str,
        timeout: int = 600,
        max_retries: int = 5,
    ):
        self.llm = ChatOpenAI(
            model=model,
            temperature=SETTINGS.model_temperature,
            timeout=timeout,
            max_retries=max_retries,
        )

    def instance(self) -> ChatOpenAI:
        return self.llm
