"""Helpers to store uploaded contract files in GCS."""

import re
from datetime import datetime, timezone

from google.cloud import storage


def _safe_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", name.strip())
    return cleaned[:180] if cleaned else "contract.pdf"


def upload_contract_file(
    settings,
    *,
    contract_id: str,
    file_name: str,
    file_bytes: bytes,
) -> str:
    """Upload a contract file to the contract bucket and return gs:// URI."""
    bucket_name = settings.contract_bucket
    if not bucket_name:
        raise RuntimeError("Contract bucket is not configured (GCS_BUCKET_CONTRAT or GCS_BUCKET).")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    object_name = f"uploads/{timestamp}_{contract_id}_{_safe_name(file_name)}"

    client = storage.Client(project=settings.gcp_project)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_string(file_bytes, content_type="application/pdf")

    return f"gs://{bucket_name}/{object_name}"
