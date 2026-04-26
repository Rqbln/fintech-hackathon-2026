"""Helpers to fetch the DORA regulation PDF from GCS."""

from google.cloud import storage


def _candidate_object_names(configured_object: str | None) -> list[str]:
    base = [
        "dora_regulation.pdf",
        "dora/dora_regulation.pdf",
        "regulations/dora_regulation.pdf",
        "dora/CELEX_32022R2554.pdf",
    ]
    if configured_object and configured_object not in base:
        return [configured_object, *base]
    return base


def fetch_dora_pdf_bytes(settings) -> tuple[bytes, str, str]:
    """Return (bytes, bucket_name, object_name) for DORA regulation PDF in GCS."""
    bucket_name = settings.dora_bucket
    if not bucket_name:
        raise RuntimeError("DORA bucket is not configured. Set GCS_BUCKET_DORA (or fallback bucket vars).")

    client = storage.Client(project=settings.gcp_project)
    bucket = client.bucket(bucket_name)

    for object_name in _candidate_object_names(settings.gcs_dora_object):
        blob = bucket.blob(object_name)
        if blob.exists():
            data = blob.download_as_bytes()
            if not data:
                raise RuntimeError(f"GCS object gs://{bucket_name}/{object_name} is empty.")
            return data, bucket_name, object_name

    # Last resort: scan first PDFs in bucket and pick first that contains "dora".
    for blob in client.list_blobs(bucket_name, max_results=200):
        name_l = blob.name.lower()
        if name_l.endswith(".pdf") and "dora" in name_l:
            data = blob.download_as_bytes()
            if not data:
                raise RuntimeError(f"GCS object gs://{bucket_name}/{blob.name} is empty.")
            return data, bucket_name, blob.name

    raise RuntimeError(
        "DORA PDF not found in GCS bucket. Set GCS_DORA_OBJECT to the exact object path "
        f"(current bucket: {bucket_name})."
    )
