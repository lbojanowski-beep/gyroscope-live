# app/util.py

import os
from typing import List
from openai import OpenAI

_EMBED_MODEL = "text-embedding-3-small"

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        _client = OpenAI(api_key=api_key)
    return _client


def embed_intent(text: str) -> List[float]:
    """
    Convert user intent into a vector embedding.
    Used for Engram similarity search.
    """
    client = _get_client()
    resp = client.embeddings.create(
        model=_EMBED_MODEL,
        input=text,
    )
    # OpenAI new API: resp.data[0].embedding
    return list(resp.data[0].embedding)