# app/memory.py
"""
Prosty lokalny wektorowy store Engramów dla Gyroscope.

Używany przez:
    from app.memory import VectorMemory

Przechowuje dane w pliku JSON obok aplikacji.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional


# Plik na dysku, np. app/vector_memory.json
MEMORY_PATH = Path(__file__).resolve().parent / "vector_memory.json"


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Prosta cosinus similarity, bez numpy."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class VectorMemory:
    """
    Bardzo prosty wektorowy store w pamięci + zapis do JSON.

    Struktura Engramu (przykład):
    {
        "intent_embedding": [...],
        "structural_embedding": [...],
        "code_embedding": [...],
        "blueprint_final": "1. ... 2. ...",
        "control_parameters": {...},
        "metadata": {
            "domain": "architect",
            "prompt": "Write a Python Snake game, clean architecture."
        }
    }
    """

    _cache: List[Dict[str, Any]] = []
    _loaded: bool = False

    @classmethod
    def _load(cls) -> None:
        if cls._loaded:
            return
        if MEMORY_PATH.exists():
            try:
                with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        cls._cache = data
            except Exception:
                cls._cache = []
        cls._loaded = True

    @classmethod
    def _save(cls) -> None:
        try:
            with open(MEMORY_PATH, "w", encoding="utf-8") as f:
                json.dump(cls._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[VectorMemory] Failed to save memory: {e}")

    @classmethod
    def store(cls, engram: Dict[str, Any]) -> None:
        """Zapisz nowy engram do pamięci + na dysk."""
        cls._load()
        cls._cache.append(engram)
        cls._save()
        print(f"[VectorMemory] Stored engram. Total count = {len(cls._cache)}")

    @classmethod
    def query_best(
        cls,
        intent_embedding: List[float],
        min_similarity: float = 0.80,
    ) -> Optional[Dict[str, Any]]:
        """
        Znajdź najlepszy pasujący engram na podstawie intent_embedding.
        Zwraca engram + dodaje pole '_similarity', albo None.
        """
        cls._load()
        if not cls._cache:
            return None

        best: Optional[Dict[str, Any]] = None
        best_sim = 0.0

        for eg in cls._cache:
            ref_vec = eg.get("intent_embedding") or []
            sim = _cosine_similarity(intent_embedding, ref_vec)
            if sim > best_sim:
                best_sim = sim
                best = eg

        if best is None or best_sim < min_similarity:
            return None

        best_with_sim = dict(best)
        best_with_sim["_similarity"] = float(best_sim)
        return best_with_sim