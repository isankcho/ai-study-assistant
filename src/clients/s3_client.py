import boto3
import io
import streamlit as st
from typing import Tuple, List
from botocore.client import Config
from streamlit.runtime.uploaded_file_manager import UploadedFile
from utils.s3_utils import make_s3_prefix, safe_filename, detect_content_type
from config.config import SETTINGS


class S3Client:
    def __init__(self, bucket: str | None = None):
        self.bucket = bucket or SETTINGS.s3_bucket
        assert self.bucket, "S3 bucket not found."
        self.s3 = self._get_s3_client()

    @st.cache_resource(show_spinner=False)
    def _get_s3_client(self):
        return boto3.client("s3", config=Config(s3={"addressing_style": "virtual"}))

    def upload_file(self, prefix: str, uploaded_file: UploadedFile) -> Tuple[str, str]:
        filename = safe_filename(uploaded_file)
        key = f"{prefix.rstrip('/')}/{filename}"
        content_type = uploaded_file.type or detect_content_type(filename)
        uploaded_file.seek(0)
        data = uploaded_file.getvalue()
        extra = {"ContentType": content_type}
        self.s3.upload_fileobj(
            Fileobj=io.BytesIO(data), Bucket=self.bucket, Key=key, ExtraArgs=extra
        )
        https_url = f"https://{self.bucket}.s3.amazonaws.com/{key}"
        return key, https_url

    def upload_files(
        self, resource_tag: str, chapter_name: str, files: List[UploadedFile]
    ) -> List[Tuple[str, str]]:
        s3_prefix = make_s3_prefix(resource_tag, chapter_name)
        key_url_list: List[Tuple[str, str]] = []
        for file in files:
            key, url = self.upload_file(prefix=s3_prefix, uploaded_file=file)
            key_url_list.append((key, url))
        return key_url_list
