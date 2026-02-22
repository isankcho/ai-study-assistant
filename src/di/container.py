from dependency_injector import containers, providers
from clients.gpt_client import GPTClient
from clients.notion_client import NotionClient
from regex import P
from tools.notion_toolset import NotionToolset
from tools.quiz_toolset import QuizToolset
from ui.chatbot_page import ChatbotPage
from ui.revision_page import RevisionPage
from ui.upload_notes_page import UploadNotesPage
from utils.prompt_utils import load_prompts
from workflows.chatbot_workflow import ChatbotWorkflow
from workflows.ingestion_workflow import IngestionWorkflow
from workflows.llm_markdown_workflow import LLMMarkdownWorkflow
from workflows.llm_quiz_evaluation_workflow import LLMQuizEvaluationWorkflow
from workflows.llm_quiz_generation_workflow import LLMQuizGenerationWorkflow
from workflows.quiz_generation_workflow import QuizGenerationWorkflow
from config.config import SETTINGS


class Container(containers.DeclarativeContainer):
    prompts = load_prompts()
    # Clients
    gpt_client_general = providers.Singleton(
        GPTClient, model=SETTINGS.openai_model_general
    )
    gpt_client_premium = providers.Singleton(
        GPTClient, model=SETTINGS.openai_model_premium
    )
    notion_client = providers.Singleton(NotionClient)

    # LLM Workflows
    llm_markdown_workflow = providers.Singleton(
        LLMMarkdownWorkflow,
        gpt_client=gpt_client_premium,
        prompts=prompts["notes_ingestion"],
    )
    llm_quiz_generation_workflow = providers.Singleton(
        LLMQuizGenerationWorkflow,
        gpt_client=gpt_client_premium,
        prompts=prompts["quiz_generation"],
    )
    llm_quiz_evaluation_workflow = providers.Singleton(
        LLMQuizEvaluationWorkflow,
        gpt_client=gpt_client_premium,
        prompts=prompts["quiz_evaluation"],
    )

    # Toolsets
    notion_toolset = providers.Singleton(NotionToolset, notion_client=notion_client)
    quiz_toolset = providers.Singleton(
        QuizToolset,
        notion_client=notion_client,
        llm_quiz_generation_workflow=llm_quiz_generation_workflow,
        llm_quiz_evaluation_workflow=llm_quiz_evaluation_workflow,
    )

    # Complex Workflows
    ingestion_workflow = providers.Singleton(
        IngestionWorkflow,
        notion_client=notion_client,
        llm_md_workflow=llm_markdown_workflow,
    )
    quiz_generation_workflow = providers.Singleton(
        QuizGenerationWorkflow,
        notion_client=notion_client,
        llm_quiz_generation_workflow=llm_quiz_generation_workflow,
    )
    chatbot_workflow = providers.Singleton(
        ChatbotWorkflow,
        gpt_client=gpt_client_general,
        prompts=prompts["chatbot"],
        notion_toolset=notion_toolset,
        quiz_toolset=quiz_toolset,
    )

    # UI Pages
    upload_notes_page = providers.Singleton(
        UploadNotesPage, ingestion_workflow=ingestion_workflow
    )
    revision_page = providers.Singleton(
        RevisionPage,
        notion_client=notion_client,
        quiz_generation_workflow=quiz_generation_workflow,
        llm_quiz_evaluation_workflow=llm_quiz_evaluation_workflow,
    )
    chatbot_page = providers.Singleton(ChatbotPage, chatbot_workflow=chatbot_workflow)
