from google.cloud import documentai_v1 as documentai

from app.config import GCP_PROJECT, DOCAI_LOCATION, DOCAI_PROCESSOR_ID


def _processor_name() -> str:
    return (
        f"projects/{GCP_PROJECT}/locations/{DOCAI_LOCATION}"
        f"/processors/{DOCAI_PROCESSOR_ID}"
    )


def _client() -> documentai.DocumentProcessorServiceClient:
    return documentai.DocumentProcessorServiceClient(
        client_options={"api_endpoint": f"{DOCAI_LOCATION}-documentai.googleapis.com"}
    )


def extract_from_bytes(content: bytes) -> dict:
    """
    Synchronous Document AI OCR on raw PDF bytes (max 15 pages).
    Returns {'total_pages': int, 'pages_text': [{'page': int, 'text': str}], 'tables': [...]}
    For PDFs > 15 pages, use batch_process_documents (out of scope for hackathon MVP).
    """
    request = documentai.ProcessRequest(
        name=_processor_name(),
        raw_document=documentai.RawDocument(content=content, mime_type="application/pdf"),
    )
    result = _client().process_document(request=request)
    return _parse(result.document)


def _parse(doc: documentai.Document) -> dict:
    full_text = doc.text
    pages_text = []
    for page in doc.pages:
        segments = page.layout.text_anchor.text_segments
        text = "".join(
            full_text[int(s.start_index): int(s.end_index)] for s in segments
        )
        pages_text.append({"page": page.page_number, "text": text})

    tables = []
    for page in doc.pages:
        for table in page.tables:
            headers = _row_texts(table.header_rows, full_text)
            body = [_row_texts([r], full_text)[0] for r in table.body_rows]
            tables.append({
                "page": page.page_number,
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
