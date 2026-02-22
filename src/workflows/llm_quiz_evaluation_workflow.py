from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from models.models import LLMQuizEvaluationInput
from clients.gpt_client import GPTClient
from typing import List, Dict
from workflows.workflow import Workflow


class LLMQuizEvaluationWorkflow(Workflow):
    def __init__(self, gpt_client: GPTClient, prompts: Dict[str, str]):
        self.gpt_client = gpt_client
        self.prompts = prompts

    def _build_messages(self, input: LLMQuizEvaluationInput) -> List[BaseMessage]:
        system_message = SystemMessage(content=self.prompts["system_prompt"])
        human_message = HumanMessage(
            content=self.prompts["human_prompt"].format(
                notes_md=input.notes_md, qna=input.qna, notion_url=input.notion_url
            )
        )
        return [system_message, human_message]

    def _coerce_input(self, payload: Dict) -> LLMQuizEvaluationInput:
        if not isinstance(payload, dict):
            raise ValueError("Input must be a dict")
        notes_md = payload.get("notes_md")
        qna = payload.get("qna")
        notion_url = payload.get("notion_url")
        if not notes_md:
            raise ValueError("notes_md is required")
        if not qna:
            raise ValueError("qna is required")
        if not notion_url:
            raise ValueError("notion_url is required")
        return LLMQuizEvaluationInput(notes_md=notes_md, qna=qna, notion_url=notion_url)

    def run(self, input: Dict) -> str:
        evaluationInput = self._coerce_input(input)
        prompt = ChatPromptTemplate.from_messages(self._build_messages(evaluationInput))
        llm = self.gpt_client.instance()
        parser = StrOutputParser()
        chain = prompt | llm | parser
        output = chain.invoke(input)
        return output
