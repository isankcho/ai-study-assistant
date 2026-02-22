import base64
from streamlit.runtime.uploaded_file_manager import UploadedFile


def convert_file_to_base64(file: UploadedFile) -> str:
    file.seek(0)
    data = file.getvalue()
    mime = (getattr(file, "type", None) or "image/jpeg").strip()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"
