import os

GCP_PROJECT = os.getenv("GCP_PROJECT", "regagent-dora-2026")
GCP_REGION = os.getenv("GCP_REGION", "europe-west9")
DOCAI_PROCESSOR_ID = os.getenv("DOCAI_PROCESSOR_ID", "9a4312989d6fb591")
DOCAI_LOCATION = os.getenv("DOCAI_LOCATION", "eu")
DOCUMENTS_BUCKET = os.getenv("DOCUMENTS_BUCKET", "regagent-documents-eu")
REFERENCE_BUCKET = os.getenv("REFERENCE_BUCKET", "regagent-reference-eu")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-multilingual-embedding-002")
