import os
from dataclasses import dataclass

from utils.load_secrets import load_env_vars


@dataclass(frozen=True)
class Settings:
    notion_token: str
    notion_knowledge_db_id: str
    notion_dsa_db_id: str
    notion_base_url: str
    openai_api_key: str
    openai_model_general: str
    openai_model_premium: str
    model_temperature: int
    aws_region: str
    s3_bucket: str
    notion_version: str
    chroma_persist_dir: str
    embed_model: str

    def __init__(self):
        load_env_vars()
        object.__setattr__(self, "notion_token", os.getenv("NOTION_TOKEN", "").strip())
        object.__setattr__(
            self,
            "notion_knowledge_db_id",
            os.getenv("NOTION_KNOWLEDGE_DATABASE_ID", "").strip(),
        )
        object.__setattr__(
            self, "notion_dsa_db_id", os.getenv("NOTION_DSA_DATABASE_ID", "").strip()
        )
        object.__setattr__(
            self, "notion_base_url", os.getenv("NOTION_BASE_URL", "").strip()
        )
        object.__setattr__(
            self, "openai_api_key", os.getenv("OPENAI_API_KEY", "").strip()
        )
        object.__setattr__(
            self, "openai_model_general", os.getenv("OPENAI_MODEL_GENERAL", "").strip()
        )
        object.__setattr__(
            self, "openai_model_premium", os.getenv("OPENAI_MODEL_PREMIUM", "").strip()
        )
        object.__setattr__(
            self, "model_temperature", int(os.getenv("MODEL_TEMPERATURE", "1").strip())
        )
        object.__setattr__(
            self, "aws_region", os.getenv("AWS_REGION", "eu-west-1").strip()
        )
        object.__setattr__(
            self,
            "s3_bucket",
            os.getenv("S3_BUCKET_NAME", "isankcho-knowledge-vault").strip(),
        )
        object.__setattr__(
            self, "notion_version", os.getenv("NOTION_VERSION", "2022-06-28")
        )
        object.__setattr__(
            self, "chroma_persist_dir", os.getenv("CHROMA_PERSIST_DIR", "").strip()
        )
        object.__setattr__(self, "embed_model", os.getenv("EMBED_MODEL", "").strip())


SETTINGS = Settings()

NOTION_HEADERS = {
    "Authorization": f"Bearer {SETTINGS.notion_token}",
    "Content-Type": "application/json",
    "Notion-Version": SETTINGS.notion_version,
}
