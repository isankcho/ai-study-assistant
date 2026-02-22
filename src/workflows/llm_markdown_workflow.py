from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from clients.gpt_client import GPTClient
from models.models import LLMChainInput
from typing import List, Dict, Any
from workflows.workflow import Workflow


class LLMMarkdownWorkflow(Workflow):
    def __init__(self, gpt_client: GPTClient, prompts: Dict[str, str]):
        self.gpt_client = gpt_client
        self.prompts = prompts

    def _build_messages(self, input: LLMChainInput) -> List[BaseMessage]:
        system_message = SystemMessage(content=self.prompts["system_prompt"])
        human_prompt = self.prompts["human_prompt"].format(
            user_instructions=input.user_instructions
        )
        human_message_content: List[str | Dict] = [
            {"type": "text", "text": human_prompt}
        ]
        for image_url in input.images_b64:
            human_message_content.append(
                {"type": "image_url", "image_url": {"url": image_url}}
            )
        human_message = HumanMessage(content=human_message_content)
        return [system_message, human_message]

    def _coerce_input(self, payload: Dict) -> LLMChainInput:
        if not isinstance(payload, dict):
            raise ValueError("Input must be a dict")
        users_instructions = payload.get("user_instructions")
        images_b64 = payload.get("images_b64")
        if not images_b64:
            raise ValueError("images_b64 is required ")
        return LLMChainInput(
            user_instructions=users_instructions, images_b64=images_b64
        )

    def run(self, input: Dict[str, Any]) -> str:
        llm_chain_input = self._coerce_input(input)
        prompt = ChatPromptTemplate.from_messages(self._build_messages(llm_chain_input))
        llm = self.gpt_client.instance()
        parser = StrOutputParser()
        chain = prompt | llm | parser
        output = chain.invoke({})
        return output
