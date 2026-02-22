import uuid
import hashlib
from datetime import datetime
from typing import List, Dict, Tuple
from langchain_openai import OpenAIEmbeddings
from langchain_core.runnables import RunnableLambda, RunnableConfig
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

# from langchain_chroma import Chroma
from utils.constants import (
    Label,
    INGESTION_WORKFLOW_STEP_COUNT,
    ChunkConstants,
)

# from clients.s3_client import upload_files_to_s3
from clients.notion_client import NotionClient
from config.config import SETTINGS

# from utils.s3_utils import slugify
from utils.image_utils import convert_file_to_base64
from utils.embedding_utils import count_tokens
from models.models import (
    InputPayload,
    B64Payload,
    MarkdownPayload,
    NotionPayload,
    EmbeddingPayload,
    ChunkMetadata,
)
from workflows.llm_markdown_workflow import LLMMarkdownWorkflow
from workflows.workflow import Workflow


class IngestionWorkflow(Workflow):

    def __init__(
        self, notion_client: NotionClient, llm_md_workflow: LLMMarkdownWorkflow
    ):
        self.notion_client = notion_client
        self.llm_md_workflow = llm_md_workflow

    def _update_progress_tracker(
        self, progress: int, label: str, config: RunnableConfig
    ):
        if config.__contains__("configurable") and config["configurable"].__contains__(  # type: ignore
            "progress_tracker"
        ):
            config["configurable"]["progress_tracker"].progress(progress / INGESTION_WORKFLOW_STEP_COUNT, text=label)  # type: ignore

    def _validate_inputs(
        self, input: InputPayload, config: RunnableConfig
    ) -> InputPayload:
        self._update_progress_tracker(0, "validating...", config)
        assert input.resource_tag, f"{Label.RESOURCE_TAG.value} is required"
        assert input.chapter_name, f"{Label.CHAPTER_NAME.value} is required"
        assert input.files, f"Please upload atleast one file"
        return input

    def _upload_to_s3(
        self, input: InputPayload, config: RunnableConfig
    ) -> InputPayload:
        self._update_progress_tracker(1, "uploading to S3...", config)
        # upload_files_to_s3(input.resource_tag, input.chapter_name, input.files)
        return input

    def _convert_to_base64(
        self, input: InputPayload, config: RunnableConfig
    ) -> B64Payload:
        self._update_progress_tracker(2, "converting images to base64...", config)
        images_b64 = [convert_file_to_base64(file) for file in input.files]
        return B64Payload(
            resource_tag=input.resource_tag,
            chapter_name=input.chapter_name,
            files=input.files,
            additional_context=input.additional_context,
            images_b64=images_b64,
        )

    def _build_markdown_for_notes(
        self, input: B64Payload, config: RunnableConfig
    ) -> MarkdownPayload:
        self._update_progress_tracker(3, "building markdown...", config)
        llm_output = self.llm_md_workflow.run(
            {
                "user_instructions": input.additional_context,
                "images_b64": input.images_b64,
            }
        )
        return MarkdownPayload(
            resource_tag=input.resource_tag,
            chapter_name=input.chapter_name,
            markdown=llm_output,
        )

    def _convert_markdown_to_notion_page(
        self, input: MarkdownPayload, config: RunnableConfig
    ) -> NotionPayload:
        self._update_progress_tracker(4, "creating notion page...", config)
        resp = self.notion_client.create_notion_page(
            title=input.chapter_name,
            resource_tag=input.resource_tag,
            markdown=input.markdown,
        )
        return NotionPayload(
            resource_tag=input.resource_tag,
            chapter_name=input.chapter_name,
            markdown=input.markdown,
            notion_resp=resp,
        )

    def _split_markdown(
        self, input: NotionPayload, config: RunnableConfig
    ) -> EmbeddingPayload:
        self._update_progress_tracker(5, "preparing markdown chunks...", config)
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=ChunkConstants.HEADERS_TO_SPLIT_ON.value
        )
        recursive_text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=ChunkConstants.CHUNK_SIZE_TOKENS.value,
            chunk_overlap=ChunkConstants.CHUNK_OVERLAP_TOKENS.value,
            length_function=count_tokens,
            separators=ChunkConstants.SEPARATORS.value,
        )
        md_header_chunks = markdown_splitter.split_text(input.markdown)
        text_split_chunks = recursive_text_splitter.split_documents(md_header_chunks)
        output_chunks: List[Document] = []
        for idx, ch in enumerate(text_split_chunks):
            ch_meta = ChunkMetadata(
                chunk_index=idx,
                chunk_count=len(text_split_chunks),
                created_at=datetime.now().isoformat(),
                doc_id=input.notion_resp["id"],
                chunk_id=str(uuid.uuid4()),
                resource_tag=input.resource_tag,
                chapter_name=input.chapter_name,
                notion_page_id=input.notion_resp["id"],
                notion_url=input.notion_resp["url"],
                content_hash=hashlib.sha256(
                    ch.page_content.encode("utf-8")
                ).hexdigest(),
            )
            output_chunks.append(
                Document(
                    page_content=ch.page_content,
                    metadata=ch_meta,
                    id=ch_meta["chunk_id"],
                )
            )
        return EmbeddingPayload(
            resource_tag=input.resource_tag,
            output_chunks=output_chunks,
        )

    def _embed_and_upsert_to_chroma(
        self, input: EmbeddingPayload, config: RunnableConfig
    ):
        self._update_progress_tracker(7, "embed and upsert to chroma...", config)
        embeddings = OpenAIEmbeddings(model=SETTINGS.embed_model)
        # vector_store = Chroma(
        #     collection_name=slugify(input.resource_tag),
        #     embedding_function=embeddings,
        #     persist_directory=SETTINGS.chroma_persist_dir,
        # )
        # vector_store.add_documents(input.output_chunks)

    def _coerce_input(self, payload: Dict) -> Tuple[InputPayload, RunnableConfig]:
        if not isinstance(payload, dict):
            raise ValueError("Input must be a dict")
        chapter_name = payload.get("chapter_name")
        resource_tag = payload.get("resource_tag")
        files = payload.get("files")
        additional_context = payload.get("additional_context")
        progress_tracker = payload.get("progress_tracker")
        if not chapter_name:
            raise ValueError("chapter_name is required")
        if not resource_tag:
            raise ValueError("resource_tag is required")
        if not files:
            raise ValueError("files is required")
        input_payload = InputPayload(
            chapter_name=chapter_name,
            resource_tag=resource_tag,
            files=files,
            additional_context=additional_context,
        )
        runnable_config = RunnableConfig(
            configurable={"progress_tracker": progress_tracker}
        )
        return (input_payload, runnable_config)

    def run(self, input: Dict) -> None:
        validate_r = RunnableLambda(self._validate_inputs)
        upload_r = RunnableLambda(self._upload_to_s3)
        convert_b64_r = RunnableLambda(self._convert_to_base64)
        build_markdown_r = RunnableLambda(self._build_markdown_for_notes)
        create_notion_page_r = RunnableLambda(self._convert_markdown_to_notion_page)
        # split_markdown_r = RunnableLambda(self._split_markdown)
        # embed_and_upsert_r = RunnableLambda(self._embed_and_upsert_to_chroma)
        chain = (
            validate_r
            | upload_r
            | convert_b64_r
            | build_markdown_r
            | create_notion_page_r
            # | split_markdown_r
            # | embed_and_upsert_r
        )
        payload = self._coerce_input(input)
        chain.invoke(input=payload[0], config=payload[1])
