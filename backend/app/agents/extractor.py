"""
Agent Extracteur -- Ingests vendor PDFs via Document AI,
extracts security guarantees, SLA tables, and audit clauses.
"""

import uuid

from app.models.schemas import ExtractedClause, SLAEntry, VendorDocument
from app.services.document_ai import extract_from_bytes
from app.services.storage import upload_document
from app.services.vector_store import VectorEntry, get_store
from app.services.vertex_ai import embed_texts

_SLA_KEYWORDS = {"rto", "rpo", "availability", "uptime", "sla", "disponibilité", "target"}


class ExtractorAgent:
    """Extracts clauses from vendor PDFs and indexes them in the vector store."""

    async def extract(
        self, content: bytes, filename: str, vendor_name: str
    ) -> VendorDocument:
        document_id = uuid.uuid4().hex[:8]

        # 1. Store original PDF in GCS
        gcs_uri = await upload_document(content, filename, document_id)

        # 2. Table-aware OCR via Document AI
        doc_result = extract_from_bytes(content)

        # 3. Clause-aligned chunking
        from app.utils.chunker import chunk_by_clause
        chunks = chunk_by_clause(doc_result["pages_text"])

        # 4. Embed all chunks via Vertex AI
        texts = [c["text"] for c in chunks]
        embeddings = await embed_texts(texts)

        # 5. Upsert into vector store
        store = get_store()
        entries = [
            VectorEntry(
                chunk_id=f"{document_id}_{c['chunk_id']}",
                doc_id=document_id,
                vendor_name=vendor_name,
                text=c["text"],
                page=c["page"],
                category=c["category"],
                embedding=embeddings[i],
            )
            for i, c in enumerate(chunks)
        ]
        store.upsert(entries)

        # 6. Build Pydantic output models
        clauses = [
            ExtractedClause(
                clause_id=f"{document_id}_{c['chunk_id']}",
                text=c["text"],
                category=c["category"],
                source_page=c["page"],
            )
            for c in chunks
        ]
        sla_entries = self._extract_sla(doc_result["tables"])

        return VendorDocument(
            document_id=document_id,
            vendor_name=vendor_name,
            document_type="contract",
            filename=filename,
            gcs_uri=gcs_uri,
            clauses=clauses,
            sla_entries=sla_entries,
        )

    async def search(
        self,
        query: str,
        doc_id: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        """Semantic search over indexed chunks. Optionally filter by doc_id."""
        embeddings = await embed_texts([query])
        return get_store().search(embeddings[0], top_k=top_k, doc_id=doc_id)

    def _extract_sla(self, tables: list[dict]) -> list[SLAEntry]:
        entries = []
        for table in tables:
            headers_lower = [h.lower() for h in table["headers"]]
            metric_col = next(
                (i for i, h in enumerate(headers_lower)
                 if any(k in h for k in _SLA_KEYWORDS)),
                None,
            )
            value_col = next(
                (i for i, h in enumerate(headers_lower)
                 if "value" in h or "valeur" in h or "target" in h),
                None,
            )
            if metric_col is not None and value_col is not None and metric_col != value_col:
                for row in table["rows"]:
                    if len(row) > max(metric_col, value_col):
                        entries.append(SLAEntry(
                            metric=row[metric_col],
                            value=row[value_col],
                        ))
        return entries
