from typing import List, Optional, Dict, TypedDict, Annotated
from pydantic import BaseModel, ConfigDict, Field
from streamlit.runtime.uploaded_file_manager import UploadedFile
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class InputPayload(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    chapter_name: str
    resource_tag: str
    files: List[UploadedFile]
    additional_context: Optional[str] | None


class B64Payload(InputPayload):
    images_b64: List[str]


class MarkdownPayload(BaseModel):
    chapter_name: str
    resource_tag: str
    markdown: str


class NotionPayload(MarkdownPayload):
    notion_resp: Dict


class EmbeddingPayload(BaseModel):
    resource_tag: str
    output_chunks: List[Document]


class LLMChainInput(BaseModel):
    user_instructions: Optional[str]
    images_b64: List[str]


class ChunkMetadata(TypedDict):
    chunk_index: int
    chunk_count: int
    created_at: str
    doc_id: str
    chunk_id: str
    resource_tag: str
    chapter_name: str
    notion_page_id: str
    notion_url: str
    content_hash: str


class Question(TypedDict):
    id: str
    text: str
    refs: List[str]


class QnA(TypedDict):
    id: str
    question: str
    answer: str


class QuizState(BaseModel):
    notion_url: str
    notion_page_id: str
    notes_md: str = ""
    n_questions: int = 10
    questions: list[Question] = Field(default_factory=list)


class LLMQuizEvaluationInput(BaseModel):
    notes_md: str
    qna: List[Dict]
    notion_url: str


class LLMQuizGenerationInput(BaseModel):
    notes_md: str
    n_questions: int


class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
