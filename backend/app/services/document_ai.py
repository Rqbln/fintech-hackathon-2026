import functools
import io

from google.cloud import documentai_v1 as documentai

from app.config import GCP_PROJECT, DOCAI_LOCATION, DOCAI_PROCESSOR_ID

_PAGE_LIMIT = 15  # OCR processor in non-imageless mode: 15 pages per request


def _processor_name() -> str:
    return (
        f"projects/{GCP_PROJECT}/locations/{DOCAI_LOCATION}"
        f"/processors/{DOCAI_PROCESSOR_ID}"
    )


@functools.lru_cache(maxsize=None)
def _client() -> documentai.DocumentProcessorServiceClient:
    return documentai.DocumentProcessorServiceClient(
        client_options={"api_endpoint": f"{DOCAI_LOCATION}-documentai.googleapis.com"}
    )


def extract_from_bytes(content: bytes) -> dict:
    """
    Synchronous Document AI OCR. Splits PDFs > 30 pages into 30-page chunks
    and merges results, preserving correct page numbers across chunks.
    """
    chunks = _split_pdf(content)
    if len(chunks) == 1:
        chunk_bytes, page_offset = chunks[0]
        return _process_chunk(chunk_bytes, page_offset=page_offset)

    merged: dict = {"total_pages": 0, "pages_text": [], "tables": []}
    for chunk_bytes, page_offset in chunks:
        partial = _process_chunk(chunk_bytes, page_offset=page_offset)
        merged["pages_text"].extend(partial["pages_text"])
        merged["tables"].extend(partial["tables"])
        merged["total_pages"] += partial["total_pages"]
    return merged


def _split_pdf(content: bytes) -> list[tuple[bytes, int]]:
    """Return list of (chunk_bytes, page_offset) tuples, each ≤ PAGE_LIMIT pages."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(content))
    total = len(reader.pages)
    if total <= _PAGE_LIMIT:
        return [(content, 0)]

    chunks = []
    for start in range(0, total, _PAGE_LIMIT):
        writer = PdfWriter()
        for i in range(start, min(start + _PAGE_LIMIT, total)):
            writer.add_page(reader.pages[i])
        buf = io.BytesIO()
        writer.write(buf)
        chunks.append((buf.getvalue(), start))
    return chunks


def _process_chunk(content: bytes, page_offset: int) -> dict:
    request = documentai.ProcessRequest(
        name=_processor_name(),
        raw_document=documentai.RawDocument(content=content, mime_type="application/pdf"),
    )
    result = _client().process_document(request=request)
    return _parse(result.document, page_offset=page_offset)


def _parse(doc: documentai.Document, page_offset: int = 0) -> dict:
    full_text = doc.text
    pages_text = []
    for page in doc.pages:
        segments = page.layout.text_anchor.text_segments
        text = "".join(
            full_text[int(s.start_index): int(s.end_index)] for s in segments
        )
        pages_text.append({"page": page.page_number + page_offset, "text": text})

    tables = []
    for page in doc.pages:
        for table in page.tables:
            headers = _row_texts(table.header_rows, full_text)
            body = [_row_texts([r], full_text)[0] for r in table.body_rows]
            tables.append({
                "page": page.page_number + page_offset,
                "headers": headers[0] if headers else [],
                "rows": body,
            })

    return {"total_pages": len(doc.pages), "pages_text": pages_text, "tables": tables}


def _row_texts(rows, full_text: str) -> list[list[str]]:
    result = []
    for row in rows:
        cells = []
        for cell in row.cells:
            segs = cell.layout.text_anchor.text_segments
            cell_text = "".join(
                full_text[int(s.start_index): int(s.end_index)] for s in segs
            ).strip()
            cells.append(cell_text)
        result.append(cells)
    return result
