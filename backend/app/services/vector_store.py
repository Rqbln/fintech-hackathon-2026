"""
Vector store with cosine similarity search.

Backend selection (controlled by VECTOR_STORE_BACKEND env var):
  - "firestore" : persists embeddings in GCP Firestore (production)
  - "memory"    : in-process dict, lost on restart (default / fallback)

The public API (VectorEntry, VectorStore, get_store) is identical in both modes
so the rest of the codebase never needs to change.
"""

import json
import logging
import math
import os
from dataclasses import dataclass

log = logging.getLogger(__name__)

# Collection name in Firestore
_COLLECTION = "vector_embeddings"


@dataclass
class VectorEntry:
    chunk_id: str
    doc_id: str
    vendor_name: str
    text: str
    page: int
    category: str
    embedding: list[float]


# ---------------------------------------------------------------------------
# In-memory backend (default)
# ---------------------------------------------------------------------------

class _MemoryStore:
    def __init__(self) -> None:
        self._entries: list[VectorEntry] = []

    def upsert(self, entries: list[VectorEntry]) -> None:
        existing = {e.chunk_id for e in self._entries}
        for e in entries:
            if e.chunk_id not in existing:
                self._entries.append(e)
                existing.add(e.chunk_id)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        doc_id: str | None = None,
    ) -> list[dict]:
        pool = (
            [e for e in self._entries if e.doc_id == doc_id]
            if doc_id else self._entries
        )
        if not pool:
            return []
        scored = sorted(pool, key=lambda e: _cosine(query_embedding, e.embedding), reverse=True)
        return [_to_dict(e, _cosine(query_embedding, e.embedding)) for e in scored[:top_k]]

    def count(self, doc_id: str | None = None) -> int:
        if doc_id:
            return sum(1 for e in self._entries if e.doc_id == doc_id)
        return len(self._entries)

    def delete_doc(self, doc_id: str) -> None:
        self._entries = [e for e in self._entries if e.doc_id != doc_id]


# ---------------------------------------------------------------------------
# Firestore backend (production)
# ---------------------------------------------------------------------------

class _FirestoreStore:
    def __init__(self) -> None:
        from google.cloud import firestore
        from app.config import GCP_PROJECT
        self._db = firestore.Client(project=GCP_PROJECT)
        self._col = self._db.collection(_COLLECTION)
        log.info("VectorStore: using Firestore backend (project=%s, collection=%s)", GCP_PROJECT, _COLLECTION)

    def upsert(self, entries: list[VectorEntry]) -> None:
        batch = self._db.batch()
        for e in entries:
            ref = self._col.document(e.chunk_id)
            batch.set(ref, {
                "chunk_id":    e.chunk_id,
                "doc_id":      e.doc_id,
                "vendor_name": e.vendor_name,
                "text":        e.text,
                "page":        e.page,
                "category":    e.category,
                # Firestore doesn't support list[float] natively — store as JSON string
                "embedding":   json.dumps(e.embedding),
            }, merge=True)
        batch.commit()

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        doc_id: str | None = None,
    ) -> list[dict]:
        if doc_id:
            docs = self._col.where("doc_id", "==", doc_id).stream()
        else:
            docs = self._col.stream()

        entries = []
        for doc in docs:
            d = doc.to_dict()
            entries.append(VectorEntry(
                chunk_id=d["chunk_id"],
                doc_id=d["doc_id"],
                vendor_name=d["vendor_name"],
                text=d["text"],
                page=d["page"],
                category=d["category"],
                embedding=json.loads(d["embedding"]),
            ))

        if not entries:
            return []

        scored = sorted(entries, key=lambda e: _cosine(query_embedding, e.embedding), reverse=True)
        return [_to_dict(e, _cosine(query_embedding, e.embedding)) for e in scored[:top_k]]

    def count(self, doc_id: str | None = None) -> int:
        if doc_id:
            return self._col.where("doc_id", "==", doc_id).count().get()[0][0].value
        return self._col.count().get()[0][0].value

    def delete_doc(self, doc_id: str) -> None:
        batch = self._db.batch()
        for doc in self._col.where("doc_id", "==", doc_id).stream():
            batch.delete(doc.reference)
        batch.commit()


# ---------------------------------------------------------------------------
# Public facade — same interface regardless of backend
# ---------------------------------------------------------------------------

class VectorStore:
    """Public wrapper — delegates to the active backend."""

    def __init__(self, backend: str = "memory") -> None:
        if backend == "firestore":
            self._backend = _FirestoreStore()
        else:
            self._backend = _MemoryStore()

    def upsert(self, entries: list[VectorEntry]) -> None:
        self._backend.upsert(entries)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        doc_id: str | None = None,
    ) -> list[dict]:
        return self._backend.search(query_embedding, top_k=top_k, doc_id=doc_id)

    def count(self, doc_id: str | None = None) -> int:
        return self._backend.count(doc_id)

    def delete_doc(self, doc_id: str) -> None:
        self._backend.delete_doc(doc_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _to_dict(e: VectorEntry, score: float) -> dict:
    return {
        "chunk_id":    e.chunk_id,
        "doc_id":      e.doc_id,
        "vendor_name": e.vendor_name,
        "text":        e.text,
        "page":        e.page,
        "category":    e.category,
        "score":       score,
    }


# ---------------------------------------------------------------------------
# Singleton — reads VECTOR_STORE_BACKEND env var at startup
# ---------------------------------------------------------------------------

def _make_store() -> VectorStore:
    backend = os.getenv("VECTOR_STORE_BACKEND", "memory")
    if backend == "firestore":
        try:
            return VectorStore(backend="firestore")
        except Exception as e:
            log.warning("Firestore init failed (%s) — falling back to memory store", e)
            return VectorStore(backend="memory")
    return VectorStore(backend="memory")


_store = _make_store()


def get_store() -> VectorStore:
    return _store
