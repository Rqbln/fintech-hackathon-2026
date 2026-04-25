"""Google Cloud Document AI client for PDF extraction."""

from google.cloud import documentai_v1 as documentai

from app.config import GCP_PROJECT, DOCAI_LOCATION, DOCAI_PROCESSOR_ID


def get_processor_name() -> str:
    return f"projects/{GCP_PROJECT}/locations/{DOCAI_LOCATION}/processors/{DOCAI_PROCESSOR_ID}"


async def process_document(content: bytes, mime_type: str = "application/pdf") -> documentai.Document:
    """Process a document through the OCR processor."""
    client = documentai.DocumentProcessorServiceClient()
    raw_document = documentai.RawDocument(content=content, mime_type=mime_type)
    request = documentai.ProcessRequest(
        name=get_processor_name(),
        raw_document=raw_document,
    )
    result = client.process_document(request=request)
    return result.document
