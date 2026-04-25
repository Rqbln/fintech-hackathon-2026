"""Google Cloud Storage client for document management."""

from google.cloud import storage

from app.config import DOCUMENTS_BUCKET, GCP_PROJECT, REFERENCE_BUCKET


def get_storage_client() -> storage.Client:
    return storage.Client(project=GCP_PROJECT)


async def upload_document(content: bytes, filename: str, document_id: str = "") -> str:
    """Upload a PDF to the documents bucket. Returns the GCS URI."""
    client = get_storage_client()
    bucket = client.bucket(DOCUMENTS_BUCKET)
    prefix = f"{document_id}_" if document_id else ""
    blob_name = f"uploads/{prefix}{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(content, content_type="application/pdf")
    return f"gs://{DOCUMENTS_BUCKET}/{blob_name}"


async def download_reference(path: str) -> bytes:
    """Download a reference file from the reference bucket."""
    client = get_storage_client()
    bucket = client.bucket(REFERENCE_BUCKET)
    blob = bucket.blob(path)
    return blob.download_as_bytes()
