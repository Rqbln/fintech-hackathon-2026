# Shipper - Developer Guide

This guide is the operational reference for local development, demo runs, and Cloud Run deployment.

## 1) Prerequisites

- Python 3.13+
- `uv`
- Node.js 20+
- Docker
- GCP project with billing enabled
- `gcloud` CLI authenticated

## 2) Local setup

```bash
git clone https://github.com/Rqbln/fintech-hackathon-2026
cd fintech-hackathon-2026

cp .env.example .env
uv sync
cd frontend && npm install && cd ..
```

Minimal `.env` to run end-to-end:
- `LLM_PROVIDER=gemini`
- `GEMINI_API_KEY=...`
- `GCP_PROJECT=...`
- `GCS_BUCKET_CONTRAT=...`
- `GCS_BUCKET_DORA=...`
- `NEO4J_PASSWORD=...`

## 3) Run locally

Start Neo4j:

```bash
make neo4j-up
```

Start backend:

```bash
make dev
```

Start frontend (new terminal):

```bash
cd frontend
npm run dev
```

Endpoints:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## 4) Local maintenance commands

```bash
make reset-graph      # wipe neo4j graph + reapply schema
make seed-dora        # seed/index dora corpus
make seed-demo        # ingest demo contract through full pipeline
make pipeline         # integration pipeline run
make neo4j-down       # stop local neo4j
```

## 5) API quick reference

- `POST /api/ingest` - upload vendor contract (returns job id)
- `GET /api/jobs/{job_id}` - poll ingestion
- `GET /api/graph` - fetch supply-chain graph
- `POST /api/gap-analysis-stream` - stream findings/progress via SSE
- `GET /api/sessions` - list sessions
- `GET /api/sessions/{session_id}/trace` - full stored report
- `GET /api/report/{session_id}` - report JSON
- `POST /api/report/{session_id}/compliant-draft.pdf` - generate compliant PDF

## 6) Cloud Run deployment (current naming)

Services:
- `shipper-backend`
- `shipper-frontend`

Artifact repo:
- `shipper`

### Full deploy

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions _GEMINI_API_KEY=YOUR_GEMINI_API_KEY,_NEO4J_URI=YOUR_NEO4J_URI,_NEO4J_USER=YOUR_NEO4J_USER,_NEO4J_PASSWORD=YOUR_NEO4J_PASSWORD
```

### Frontend-only deploy

```bash
gcloud builds submit --config cloudbuild.frontend.yaml \
  --substitutions _BACKEND_API_BASE=https://shipper-backend-<project-number>.europe-west1.run.app
```

### Public access (if needed)

```bash
gcloud run services add-iam-policy-binding shipper-frontend --region europe-west1 --member="allUsers" --role="roles/run.invoker"
gcloud run services add-iam-policy-binding shipper-backend --region europe-west1 --member="allUsers" --role="roles/run.invoker"
```

## 7) Troubleshooting

### Neo4j connection refused
- Run `make neo4j-up`
- Wait a few seconds and retry `make reset-graph` or backend startup

### Ingest failed 500
- Check backend logs first
- Verify `.env` buckets/project/API key values
- Verify contract PDF is valid and readable

### Frontend uses old UI after deploy
- Hard refresh browser (`Ctrl+Shift+R`)
- Confirm URL is the latest `shipper-frontend` service URL

### Cloud Build 404 on session trace
- Usually stale `session_id` references after restart
- Re-run a fresh analysis and retry

## 8) Final demo recommendations

- Use `LLM_PROVIDER=gemini` for stable latency
- Keep backend min instances > 0 in Cloud Run for better responsiveness
- Reset graph before demo if you need a clean storyline: `make reset-graph`
