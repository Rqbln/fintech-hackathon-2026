# RegAgent — DORA Compliance Platform

## Project Overview

Multi-agent platform for Third-Party Risk Management under DORA regulation. Extracts compliance clauses from vendor PDFs (contracts, SLAs, SOC 2 reports) and runs automated analysis.

## Architecture

```
frontend (React + Vite)  →  nginx proxy /api/*  →  backend (FastAPI)  →  GCS / Vertex AI / Document AI
```

- **Frontend** : React + TypeScript + Vite, served by nginx on Cloud Run
- **Backend** : FastAPI (Python 3.12), served by uvicorn on Cloud Run
- **Storage** : Google Cloud Storage (`regagent-documents-eu`, `regagent-reference-eu`)
- **AI** : Vertex AI Gemini (`gemini-2.5-flash`), Document AI (processor `9a4312989d6fb591` in `eu`)

## GCP Resources

| Resource | Value |
|---|---|
| Project | `regagent-dora-2026` |
| Region | `europe-west9` |
| Documents bucket | `regagent-documents-eu` |
| Reference bucket | `regagent-reference-eu` |
| Runtime SA | `regagent-runtime-sa@regagent-dora-2026.iam.gserviceaccount.com` |
| CI/CD SA | `github-actions-sa@regagent-dora-2026.iam.gserviceaccount.com` |
| Backend URL | `https://regagent-backend-85716527673.europe-west9.run.app` |

## Key Files

| File | Role |
|---|---|
| `backend/app/main.py` | FastAPI entrypoint, router registration |
| `backend/app/config.py` | All env vars with defaults |
| `backend/app/routers/documents.py` | `POST /api/documents/upload`, `GET /api/documents/` |
| `backend/app/services/storage.py` | GCS client: upload, list, download |
| `backend/app/agents/extractor.py` | ExtractorAgent: GCS + Document AI + chunker + RAG |
| `frontend/src/components/ContractUpload.tsx` | Multi-file upload UI with real API call |
| `frontend/nginx.conf` | Nginx reverse proxy, `client_max_body_size 200M` |
| `.github/workflows/deploy-backend.yml` | CI/CD backend → Cloud Run (triggers on `main` and `dev`) |
| `.github/workflows/deploy-frontend.yml` | CI/CD frontend → Cloud Run (triggers on `main` and `dev`) |

## Local Development

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
gcloud auth application-default login
uvicorn app.main:app --reload --port 8080

# Frontend (separate terminal)
cd frontend
npm install
npm run dev   # proxy /api → http://localhost:8080
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/documents/upload` | Upload 1–N PDFs (multipart `files` + optional `vendor_name`), runs full extraction pipeline |
| `GET` | `/api/documents/` | List documents (in-memory extraction results + GCS objects) |
| `GET` | `/api/documents/{id}` | Get a specific extracted document |
| `GET` | `/health` | Health check |

### Upload curl example
```bash
curl -F "files=@/path/a.pdf" -F "files=@/path/b.pdf" -F "vendor_name=AWS" \
  https://regagent-backend-85716527673.europe-west9.run.app/api/documents/upload
```

## CI/CD

- Workflows trigger on push to **`main`** and **`dev`**.
- Frontend nginx reads `BACKEND_URL` env var at container start (envsubst). Set to backend Cloud Run URL in `deploy-frontend.yml`.
- Auth via Workload Identity Federation (no stored keys).

## Known Constraints

- PDFs only, max 50 MB per file. nginx limit set to 200 MB total.
- GCS paths use UUID prefix — never overwrites existing objects.
- ADC used everywhere (no static keys). Runtime SA needs `roles/storage.objectAdmin` on `regagent-documents-eu`.
- In-memory `_store` in documents router is ephemeral — resets on Cloud Run container restart.
