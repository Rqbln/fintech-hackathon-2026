# Shipper - DORA AI Analyst

AI-powered DORA compliance platform for financial institutions.

Upload ICT vendor contracts -> build supply-chain graph -> run explainable gap analysis against DORA Article 30 -> generate remediation and compliant draft outputs.

## What this repo contains

- **Backend**: FastAPI + LlamaIndex workflows + Neo4j + Vertex AI Vector Search
- **Frontend**: Next.js SaaS UI (`Dashboard`, `Risk Map`, `Document Analysis`, `Remediation Register`)
- **Deployment**: Docker + Cloud Run + Cloud Build (`shipper-backend`, `shipper-frontend`)

## Quick Start (Local)

### 1) Setup environment

```bash
cp .env.example .env
```

Fill at least:
- `GEMINI_API_KEY`
- `GCP_PROJECT`
- `GCS_BUCKET_CONTRAT`
- `GCS_BUCKET_DORA`
- `NEO4J_PASSWORD`

### 2) Install dependencies

```bash
uv sync
cd frontend && npm install && cd ..
```

### 3) Start local services

```bash
make neo4j-up
```

Terminal A (backend):
```bash
make dev
```

Terminal B (frontend):
```bash
cd frontend
npm run dev
```

Open:
- Frontend: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### 4) Optional: start from clean graph

```bash
make reset-graph
```

## Demo flow

1. Open dashboard and upload a contract
2. Wait for ingest pipeline completion
3. Open `Risk Map` to inspect institution -> contract -> vendor/subcontractor links
4. Click a node to open `Document Analysis`
5. Review streamed findings and PDF evidence highlighting
6. Check summary lines in `Remediation Register`

## Tech stack

| Layer | Tech |
|---|---|
| API | FastAPI |
| Agent orchestration | LlamaIndex Workflows |
| LLM | Gemini (default), optional Cerebras |
| Embeddings | Gemini Embedding 2 (768) |
| Vector store | Vertex AI Vector Search v2 |
| Graph DB | Neo4j (local Docker or AuraDB) |
| Frontend | Next.js + React + Tailwind + `@xyflow/react` |
| Package managers | `uv`, `npm` |

## Cloud Run deployment

Full deploy (backend + frontend):

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions _GEMINI_API_KEY=YOUR_GEMINI_API_KEY,_NEO4J_URI=YOUR_NEO4J_URI,_NEO4J_USER=YOUR_NEO4J_USER,_NEO4J_PASSWORD=YOUR_NEO4J_PASSWORD
```

Frontend-only deploy:

```bash
gcloud builds submit --config cloudbuild.frontend.yaml \
  --substitutions _BACKEND_API_BASE=https://shipper-backend-<project-number>.europe-west1.run.app
```

## Useful commands

```bash
make dev              # run backend
make neo4j-up         # start local neo4j
make neo4j-down       # stop local neo4j
make reset-graph      # wipe graph + reapply schema
make seed-dora        # index DORA references
make seed-demo        # demo ingest pipeline
make pipeline         # integration pipeline test
```

## Notes for final demo stability

- Keep `LLM_PROVIDER=gemini` and `FAST_MODE=true` for consistent latency.
- Use persistent Cloud Run minimum instances to reduce cold starts.
- If UI looks stale after deploy, hard refresh browser cache.

## Project structure

```text
app/                  backend app
frontend/             next.js app
scripts/              seed/reset/benchmark scripts
tests/                unit + integration tests
cloudbuild.yaml       full cloud deploy
cloudbuild.frontend.yaml  frontend cloud deploy
```
