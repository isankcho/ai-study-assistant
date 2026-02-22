import tiktoken


def count_tokens(text: str) -> int:
    _ENC = tiktoken.get_encoding("cl100k_base")
    return len(_ENC.encode(text))
