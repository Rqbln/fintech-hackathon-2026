"""
Agent Extracteur -- Ingests vendor PDFs via Document AI,
extracts security guarantees, SLA tables, and audit clauses.
"""

import uuid

from app.models.schemas import ExtractedClause, SLAEntry, VendorDocument
from app.services.document_ai import extract_from_bytes
from app.services.rag_engine import get_or_create_corpus, upload_text_to_corpus
from app.services.storage import upload_document

_SLA_KEYWORDS = {"rto", "rpo", "availability", "uptime", "sla", "disponibilité", "target"}


class ExtractorAgent:
    """Extracts clauses from vendor PDFs and indexes them in the RAG corpus."""

    async def extract(
        self, content: bytes, filename: str, vendor_name: str
    ) -> VendorDocument:
        document_id = uuid.uuid4().hex[:8]

        # 1. Store original PDF in GCS (document_id prefix prevents filename collisions)
        gcs_uri = await upload_document(content, filename, document_id)

        # 2. Table-aware OCR via Document AI (synchronous — acceptable for MVP)
        doc_result = extract_from_bytes(content)

        # 3. Clause-aligned chunking
        from app.utils.chunker import chunk_by_clause  # local import avoids circular
        chunks = chunk_by_clause(doc_result["pages_text"])

        # 4. Upload all chunks as one annotated text file to RAG corpus
        corpus_name = get_or_create_corpus()
        upload_text_to_corpus(
            corpus_name=corpus_name,
            text=self._format_for_rag(vendor_name, document_id, chunks),
            display_name=f"contract_{vendor_name}_{document_id}",
            chunk_size=800,
            chunk_overlap=100,
        )

        # 5. Build Pydantic output models
        clauses = [
            ExtractedClause(
                clause_id=f"{document_id}_{chunk['chunk_id']}",
                text=chunk["text"],
                category=chunk["category"],
                source_page=chunk["page"],
            )
            for chunk in chunks
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

    def _format_for_rag(self, vendor_name: str, doc_id: str, chunks: list[dict]) -> str:
        header = f"VENDOR CONTRACT: {vendor_name}\nDOCUMENT_ID: {doc_id}\n\n"
        parts = [
            f"[PAGE {c['page']} | CATEGORY: {c['category']}]\n{c['text']}"
            for c in chunks
        ]
        return header + "\n---\n".join(parts)

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
