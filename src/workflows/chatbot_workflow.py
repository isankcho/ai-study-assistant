from typing import Any, Dict
from clients.gpt_client import GPTClient
from langgraph.graph import StateGraph, START
from langchain.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.prebuilt import ToolNode, tools_condition
from models.models import ChatState
from tools.notion_toolset import NotionToolset
from tools.quiz_toolset import QuizToolset
from workflows.workflow import Workflow
from langchain_core.runnables import RunnableConfig


class ChatbotWorkflow(Workflow):
    """
    Workflow class for managing the chatbot agent and its tool interactions.
    """

    def __init__(
        self,
        gpt_client: GPTClient,
        prompts: Dict[str, str],
        notion_toolset: NotionToolset | None = None,
        quiz_toolset: QuizToolset | None = None,
    ):
        self.gpt_client = gpt_client
        self.prompts = prompts
        self.prompt_template = self._initialize_prompt_template()
        self.notion_toolset = notion_toolset
        self.quiz_toolset = quiz_toolset
        self.tools = self._initialize_tools()
        self.llm = self._initialize_llm()
        self.graph = self._build_graph()
        self.graph_compiled = self.graph.compile()

    def _initialize_prompt_template(self):
        return ChatPromptTemplate.from_messages(
            [SystemMessage(content=self.prompts["system_prompt"])]
        )

    def _initialize_tools(self):
        tools = []
        if self.notion_toolset:
            tools += self.notion_toolset.as_tools()
        if self.quiz_toolset:
            tools += self.quiz_toolset.as_tools()
        return tools

    def _initialize_llm(self):
        return self.gpt_client.instance().bind_tools(self.tools)

    def agent_node(self, state: ChatState):
        history = state["messages"]
        system_message = self.prompt_template.format_messages()
        history_wo_system = [m for m in history if not isinstance(m, SystemMessage)]
        formatted_messages = system_message + history_wo_system
        response = self.llm.invoke(formatted_messages)
        return {"messages": [response]}

    def _build_graph(self):
        graph = StateGraph(ChatState)
        graph.add_node("agent", self.agent_node)
        graph.add_node("tools", ToolNode(self.tools))
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", tools_condition)
        graph.add_edge("tools", "agent")
        return graph

    def _coerce_input(self, input: Any) -> ChatState:
        """
        Validate and coerce the input to ChatState.

        Args:
            input (Any): The input to the workflow.

        Returns:
            ChatState: The validated chat state.

        Raises:
            ValueError: If input is invalid.
        """
        if not isinstance(input, dict):
            raise ValueError("Input must be a dict")
        messages = input.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("Input must contain a non-empty 'messages' list")
        return ChatState(messages=messages)

    def run(self, input: Dict[str, BaseMessage]) -> Dict:
        """
        Run the chatbot workflow with the provided input.

        Args:
            input (Any): The input containing the conversation history.

        Returns:
            Any: The output from the compiled graph.
        """
        state = self._coerce_input(input)
        return self.graph_compiled.invoke(state, RunnableConfig(recursion_limit=10))
