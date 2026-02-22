from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from clients.gpt_client import GPTClient
from models.models import LLMQuizGenerationInput
from typing import List, Dict, Any
from workflows.workflow import Workflow


class LLMQuizGenerationWorkflow(Workflow):
    def __init__(self, gpt_client: GPTClient, prompts: Dict[str, str]):
        self.gpt_client = gpt_client
        self.prompts = prompts

    def _build_messages(self, input: LLMQuizGenerationInput) -> List[BaseMessage]:
        system_message = SystemMessage(content=self.prompts["system_prompt"])
        human_message = HumanMessage(
            content=self.prompts["human_prompt"].format(
                notes_md=input.notes_md, n_questions=input.n_questions
            )
        )
        return [system_message, human_message]

    def _coerce_input(self, payload: Dict[str, Any]) -> LLMQuizGenerationInput:
        if not isinstance(payload, dict):
            raise ValueError("Input must be a dict")
        notes_md = payload.get("notes_md")
        n_questions = payload.get("n_questions")
        if not notes_md:
            raise ValueError("notes_md is required")
        if not n_questions:
            raise ValueError("n_questions is required")
        return LLMQuizGenerationInput(notes_md=notes_md, n_questions=n_questions)

    def run(self, input: Dict[str, Any]) -> Dict[str, Any]:
        quiz_generation_input = self._coerce_input(input)
        prompt = ChatPromptTemplate.from_messages(
            self._build_messages(quiz_generation_input)
        )
        llm = self.gpt_client.instance()
        parser = JsonOutputParser()
        chain = prompt | llm | parser
        output = chain.invoke(input)
        return output
