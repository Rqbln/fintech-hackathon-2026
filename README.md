# DORA AI Analyst

> *The AI analyst for DORA, not another compliance dashboard.*

AI-powered DORA (EU 2022/2554) compliance analysis for EU financial institutions. Upload third-party vendor contracts → AI extracts obligations, maps dependency risk as an interactive graph → streams a gap analysis with PDF citations → proposes EU-sovereign remediation paths.

**Live demo:** deployed on Google Cloud Run.

---

## What it does

1. **Upload** vendor contracts (PDF). The AI pipeline extracts vendor names, services, sub-vendor chains, and which DORA Art.30 obligations are covered — with source citations.

2. **Risk graph** — Neo4j + Sigma.js WebGL graph with your bank at the centre. Vendors sized by criticality score (contract count × services × sub-vendor depth × country risk). Dependency arrows show 4th-party chains. Node colour shifts from blue → amber → red as gap analysis results arrive.

3. **Gap analysis** — 12 DORA Art.30 obligations evaluated in parallel via LLM, streamed one by one as verdicts are ready. Each finding cites verbatim contract language and links to the exact PDF page with a yellow highlight.

4. **Remediation** — AI proposes prioritised fixes with EU-sovereign vendor alternatives (OVHcloud, 3DS Outscale, Scaleway, etc.) including cost delta and SecNumCloud certification status.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.136+ · Python 3.13 · uv |
| AI agents | LlamaIndex Workflows 2.15+ |
| LLM | Cerebras `llama3.1-8b` (OpenAI-compatible, 100 RPM) |
| Embeddings | Gemini Embedding 2 (768-dim MRL) |
| Vector store | Vertex AI Vector Search v2 |
| Graph DB | Neo4j 5.26 (local Docker / Cloud Run sidecar) |
| Document storage | Google Cloud Storage |
| Frontend | Next.js 16 · React 19 · Tailwind CSS v4 |
| Graph visualisation | Sigma.js v3 + graphology (WebGL, ForceAtlas2) |
| Animations | Framer Motion |
| PDF citations | PyMuPDF (server-side highlight annotations) |
| Deployment | Google Cloud Run (multi-container — backend + Neo4j sidecar) |

---

## Quick start (local)

```bash
# 1. Clone
git clone https://github.com/Rqbln/fintech-hackathon-2026
cd fintech-hackathon-2026

# 2. Install Python dependencies
uv sync

# 3. Copy and fill env vars
cp .env.example .env   # set CEREBRAS_API_KEY, GEMINI_API_KEY, GCP_PROJECT, GCS_BUCKET

# 4. Authenticate GCP
gcloud auth application-default login

# 5. Start Neo4j
make neo4j-up

# 6. Start the API
make dev              # → http://localhost:8000

# 7. Start the frontend (separate terminal)
cd frontend && npm install && npm run dev   # → http://localhost:3000
```

See [HOWTO.md](HOWTO.md) for full setup instructions including GCP APIs and billing.

---

## Deploy to Google Cloud Run

```bash
# One command — builds both images, deploys backend (with Neo4j sidecar) + frontend
./deploy.sh
```

The deploy script:
- Builds and pushes the FastAPI backend image to GCR
- Deploys it as a multi-container Cloud Run service (backend + Neo4j sidecar sharing `localhost:7687`)
- Builds the Next.js frontend with the backend URL baked in
- Deploys the frontend as a separate Cloud Run service
- Prints both URLs on completion

---

## Project structure

```
app/
├── agents/        AI pipeline — extraction, graph builder, gap analysis, remediation, report
├── api/           FastAPI routers — ingest, graph, analysis, documents, report, sessions
├── graph/         Neo4j client, schema, upsert, entity resolution, queries
├── llm/           LLM + embedding factories, retry logic
├── rag/           Vertex AI VS store, PDF ingestion pipeline, citation query engine
├── schemas/       Pydantic models (single source of truth for all data shapes)
├── data/          dora_obligations.yaml (12 Art.30 obligations) · sovereign_alternatives.yaml
└── contract_store.py   In-memory contract text store (populated during ingest)

frontend/
├── src/app/       Next.js App Router pages (upload · graph)
├── src/components/
│   ├── graph/     GraphCanvas · VendorPanel · PortfolioPanel · FindingCard · CitationModal
│   └── upload/    DropZone · ProcessingFeed
└── src/lib/       API client · TypeScript types · utilities

Dockerfile              Backend container (python:3.13-slim + uv)
frontend/Dockerfile     Frontend container (node:22-alpine, Next.js standalone)
cloud-run-backend.yaml  Cloud Run multi-container spec (backend + neo4j sidecar)
deploy.sh               One-command Cloud Run deployment script
docker-compose.yml      Local Neo4j only
```

---

## Key endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check — Neo4j, LLM keys, Vector Store |
| `POST` | `/api/ingest` | Upload contract PDF → `{job_id}` (async) |
| `GET` | `/api/jobs/{job_id}` | Poll pipeline status |
| `GET` | `/api/graph` | Sigma.js-ready graph JSON |
| `POST` | `/api/gap-analysis-stream` | SSE-streamed gap analysis |
| `GET` | `/api/documents/{id}/pdf` | Serve PDF with highlight annotations |
| `GET` | `/api/documents/{id}/find-text?q=...` | Find page number for a quote |
| `GET` | `/api/contracts/{id}/preview` | Retrieve stored contract text |
| `GET` | `/api/report/{session_id}/markdown` | Download audit report as Markdown |

Full interactive docs: `http://localhost:8000/docs`
