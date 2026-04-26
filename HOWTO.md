# DORA AI Analyst — Developer Guide

AI-powered DORA (EU 2022/2554) compliance platform. Upload vendor contracts → AI extracts structured data with citations → builds a Neo4j dependency graph → runs parallel gap analysis against 12 DORA Art.30 obligations → proposes EU-sovereign remediation paths.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.13+ | `pyenv install 3.13` |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node.js | 22+ | `nvm install 22` |
| Docker | any | [docker.com](https://docs.docker.com/get-docker/) |
| GCP account | — | with billing enabled |
| `gcloud` CLI | latest | `brew install google-cloud-sdk` |

---

## 1. Clone and install

```bash
git clone https://github.com/Rqbln/fintech-hackathon-2026
cd fintech-hackathon-2026

# Python backend
uv sync

# Next.js frontend
cd frontend && npm install && cd ..
```

---

## 2. Environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
# LLM
LLM_PROVIDER=cerebras
CEREBRAS_API_KEY=csk-...        # https://inference.cerebras.ai → API Keys
CEREBRAS_MODEL=llama3.1-8b

# Embeddings
GEMINI_API_KEY=AIza...          # https://aistudio.google.com → Get API key

# GCP
GCP_PROJECT=your-project-id
GCP_REGION=us-central1          # do not change — Vertex AI VS only in us-central1
GCS_BUCKET=your-bucket-name

# Vertex AI Vector Search
VERTEX_AI_VS_COLLECTION=dora-analyst-docs

# Neo4j (local dev)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
```

**Never commit `.env`** — it is gitignored.

---

## 3. GCP setup

```bash
# Authenticate
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# Enable APIs
gcloud services enable \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com

# Create GCS bucket
gsutil mb -l us-central1 gs://YOUR_BUCKET_NAME
```

Vertex AI Vector Search v2 requires billing:
```bash
gcloud billing projects link YOUR_PROJECT_ID --billing-account=YOUR_BILLING_ACCOUNT_ID
# Find billing accounts: gcloud billing accounts list
```

---

## 4. Start Neo4j (local)

```bash
# Add yourself to docker group (first time only)
sudo usermod -aG docker $USER && newgrp docker

make neo4j-up
# Neo4j browser: http://localhost:7474 (neo4j / password from .env)
```

---

## 5. Start the backend

```bash
make dev
# → http://localhost:8000/docs   (Swagger)
# → http://localhost:8000/health
```

On startup the server connects to Neo4j, Vertex AI VS, and initialises the LLM + embedding models. All badges at `/health` should show `ok`.

---

## 6. Start the frontend

```bash
cd frontend && npm run dev
# → http://localhost:3000
```

The frontend proxies all `/api/*` requests to the backend at `localhost:8000` (configured in `next.config.ts`).

---

## 7. Seed DORA regulation

Index the DORA regulation PDF into Vertex AI Vector Search (run once):

```bash
curl -X POST http://localhost:8000/api/ingest/dora
# → {"status": "ingested", "document_id": "DORA-2022-2554-EN", "nodes": 178}
```

---

## 8. Frontend walkthrough

### Upload page (`/`)

1. Drop one or more vendor contract PDFs onto the drop zone.
2. Each file shows a live processing feed as the 4-step pipeline runs:
   **Parsing PDF → Embedding into Vector Store → Extracting vendor data → Building graph → Scoring risks**
3. Click **View Risk Graph** when done (always available even with an empty graph).

### Graph page (`/graph`)

- **The graph** — your bank at centre (navy node), vendor nodes sized by criticality score. DEPENDS_ON arrows show sub-vendor chains. Dot-grid texture background.
- **Colours before analysis** — node colour = criticality score (blue / amber / red by risk level).
- **Colours after analysis** — node colour = compliance ratio: emerald (≥60% met) / amber (≥30%) / red (<30%). Persists in `localStorage` across page refreshes.
- **Click a vendor** — camera flies to that node, VendorPanel slides in and immediately starts streaming gap analysis.
- **Portfolio button** (navbar) — PortfolioPanel lists all vendors ranked by risk with EU/non-EU badges and score bars.
- **ECB Report button** — downloads a Markdown audit report (appears after first analysis).

### VendorPanel (slides in on vendor click)

- **Header** — vendor name, country, risk badge, ⚡ cached badge on repeat clicks.
- **Progress bar** — streams `N / 12` as each DORA obligation is evaluated.
- **Findings tab** — AI Summary (rendered markdown) followed by 12 findings. Each finding shows: verdict icon, article reference, risk badge, rationale, gap description, evidence quotes, and a **See in PDF** button.
- **Remediation tab** — appears when analysis completes. One card per gap with a remediation plan and EU-sovereign alternatives.

### CitationModal (opens on "See in PDF")

The backend:
1. Calls `GET /api/documents/{id}/find-text?q=...` to locate the exact page.
2. Serves `GET /api/documents/{id}/pdf?highlight=...` with PyMuPDF highlight annotations baked in.

The modal renders the PDF inline, jumps to the cited page, and shows the highlighted clause.

---

## 9. Makefile reference

```
make dev           Start API server (hot-reload, port 8000)
make neo4j-up      Start Neo4j in Docker
make neo4j-down    Stop Neo4j
make lint          ruff check
make fmt           ruff format
make test          Run all tests
```

---

## 10. Deploy to Cloud Run

```bash
# One-time setup
gcloud auth configure-docker gcr.io
chmod +x deploy.sh

# Deploy everything
./deploy.sh
```

The script deploys:
- **`dora-backend`** — multi-container Cloud Run service: FastAPI backend + Neo4j 5.26 sidecar sharing `localhost:7687`. No external Neo4j account needed.
- **`dora-frontend`** — Next.js standalone server. Backend URL baked in at build time.

Both services are publicly accessible. URLs printed at the end of the script.

First deployment takes ~3 minutes (Neo4j boot time). Subsequent deployments are faster.

---

## 11. Architecture notes

**Gap analysis** — 12 DORA Art.30 obligations evaluated in parallel (semaphore capped at 4 concurrent LLM calls). Results streamed via SSE as each one completes. First finding appears in ~1-2 seconds. Results cached in-memory — second click on same vendor is instant.

**Contract text** — stored in `contract_store.py` (in-memory, up to 20,000 chars per contract) during ingest. Fetched by VendorPanel before starting gap analysis. Cleared on server restart — re-upload contract to repopulate.

**Graph** — only Vendor nodes and DEPENDS_ON edges are returned by the graph API. Service/Contract/DORAObligation nodes are stored in Neo4j but not displayed (keeps the graph readable).

**PDF highlighting** — PyMuPDF `page.search_for(phrase)` does exact substring match. Works on text-layer PDFs; silently skips scanned/image-only PDFs.

---

## 12. Common issues

**Neo4j connection refused** → Run `make neo4j-up` and wait 10s.

**`google.auth.exceptions.DefaultCredentialsError`** → Run `gcloud auth application-default login`.

**Gap analysis shows empty contract text** → Contract text store is in-memory; re-upload the contract after server restart.

**Docker permission denied** → `sudo usermod -aG docker $USER && newgrp docker`

**Cloud Run OOM on startup** → Check `cloud-run-backend.yaml` has `memory: 1500Mi` for the neo4j container and `NEO4J_server_jvm_additional: "-XX:MaxRAMPercentage=60.0"`.

**All findings show `unmet`** → The contract text was empty during analysis. The strict LLM prompt requires explicit contractual language — `unmet` is the correct verdict when text is absent.
