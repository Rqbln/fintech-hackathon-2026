"""Google Cloud Storage client for document management."""

import uuid
from typing import Any

from google.cloud import storage

from app.config import DOCUMENTS_BUCKET, GCP_PROJECT, REFERENCE_BUCKET


def get_storage_client() -> storage.Client:
    return storage.Client(project=GCP_PROJECT)


async def upload_document(content: bytes, filename: str, document_id: str = "") -> str:
    """Upload a PDF to the documents bucket. Returns the GCS URI."""
    client = get_storage_client()
    bucket = client.bucket(DOCUMENTS_BUCKET)
    prefix = f"{document_id}_" if document_id else f"{uuid.uuid4()}_"
    blob_name = f"uploads/{prefix}{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(content, content_type="application/pdf")
    return f"gs://{DOCUMENTS_BUCKET}/{blob_name}"


def list_objects(prefix: str = "uploads/") -> list[dict[str, Any]]:
    """List objects in the documents bucket under the given prefix."""
    client = get_storage_client()
    bucket = client.bucket(DOCUMENTS_BUCKET)
    results = []
    for blob in bucket.list_blobs(prefix=prefix):
        results.append({
            "object_name": blob.name,
            "gcs_uri": f"gs://{DOCUMENTS_BUCKET}/{blob.name}",
            "size": blob.size,
            "updated": blob.updated.isoformat() if blob.updated else None,
        })
    return results


async def download_reference(path: str) -> bytes:
    """Download a reference file from the reference bucket."""
    client = get_storage_client()
    bucket = client.bucket(REFERENCE_BUCKET)
    blob = bucket.blob(path)
    return blob.download_as_bytes()
