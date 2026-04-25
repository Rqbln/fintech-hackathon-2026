# DORA AI Analyst — Developer Guide

AI-powered DORA (EU 2022/2554) compliance platform. Uploads vendor contracts,
extracts structured data with citations, maps a dependency graph in Neo4j,
runs gap analysis against 12 DORA Art.30 obligations, and proposes EU-sovereign
remediation paths.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.13+ | `pyenv install 3.13` |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker | any | [docker.com](https://docs.docker.com/get-docker/) |
| GCP account | — | with billing enabled |
| `gcloud` CLI | latest | `brew install google-cloud-sdk` |

---

## 1. Clone and install

```bash
git clone https://github.com/Rqbln/fintech-hackathon-2026
cd fintech-hackathon-2026
git checkout bogdan

# Install all dependencies (creates .venv automatically)
uv sync
```

---

## 2. Environment variables

Copy the example and fill in your keys:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# ── Required ──────────────────────────────────────────────────────────────────
CEREBRAS_API_KEY=csk-...          # https://inference.cerebras.ai → API Keys
GEMINI_API_KEY=AIza...            # https://aistudio.google.com → Get API key
GCP_PROJECT=your-project-id      # gcloud projects list
GCS_BUCKET=your-bucket-name      # must exist in the same project
NEO4J_PASSWORD=your-password     # any string for local dev

# ── Optional (defaults work fine) ─────────────────────────────────────────────
CEREBRAS_MODEL=llama3.1-8b
GCP_REGION=us-central1           # DO NOT change — Vertex AI VS v2 only in us-central1
VERTEX_AI_VS_COLLECTION=dora-analyst-docs
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
```

**Never commit `.env`** — it is in `.gitignore`.

---

## 3. GCP setup

### 3a. Authenticate

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### 3b. Enable APIs

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  vectorsearch.googleapis.com
```

### 3c. Create GCS bucket (if it doesn't exist)

```bash
gsutil mb -l us-central1 gs://YOUR_BUCKET_NAME
```

### 3d. Billing

Vertex AI Vector Search v2 requires a billing account. Link one:

```bash
gcloud billing projects link YOUR_PROJECT_ID \
  --billing-account=YOUR_BILLING_ACCOUNT_ID
# Find billing accounts: gcloud billing accounts list
```

---

## 4. Start Neo4j

```bash
# Requires Docker and user in the docker group
sudo usermod -aG docker $USER && newgrp docker   # first time only

make neo4j-up
# Neo4j browser: http://localhost:7474 (user: neo4j, pass: from .env)
```

---

## 5. Seed DORA regulation

Downloads the official DORA PDF and indexes 178 chunks into Vertex AI Vector Search.
Run once — the result is cached:

```bash
make seed-dora
# Or: uv run python scripts/seed_dora.py
```

Expected output:
```
Downloading DORA PDF…
pdf_parsed  pages=74
pdf_indexed nodes=178
✓ DORA seeded
```

---

## 6. Start the API server

```bash
make dev
# → http://localhost:8000        (test UI)
# → http://localhost:8000/docs   (Swagger)
```

On startup the server:
1. Connects to Neo4j and applies constraints/indexes
2. Creates the LLM (Cerebras `llama3.1-8b`)
3. Creates Gemini Embedding 2 (768-dim)
4. Connects to Vertex AI Vector Search collection `dora-analyst-docs`
5. Creates the `ContractIngestionWorkflow` instance

If startup fails with `degraded` status at `/health`, check:
- Neo4j is running (`make neo4j-up`)
- All `.env` keys are set
- `gcloud auth application-default login` was run

---

## 7. Demo: seed and test the pipeline

```bash
# Ingest the demo AWS contract through the full AI pipeline
make seed-demo
# → prints extraction results, graph nodes, risk scores

# Run full 6-step integration test
make pipeline
```

---

## 8. Test UI walkthrough

Open **http://localhost:8000** in your browser.

### Status tab
- Click **Refresh** — all badges should be green.
- Session state (bottom) updates automatically as you work.

### Ingest tab

1. **Seed DORA** — click once, wait for `already_ingested` or `ingested` response.
2. **Upload contract** — select a PDF, optionally set a Contract ID, click **Upload & Analyse**.
   - Returns a `job_id` immediately.
   - The UI polls every 2 seconds until the pipeline finishes (~30–90 s).
   - On success, vendor name + criticality score appear in the session state bar.
   - Gap Analysis form is pre-filled with `contract_id` and `vendor_name`.
3. **Concentration ranking** — click **Load** to see all vendors sorted by risk score.

### Graph tab

- Leave root vendor blank → full graph.
- Type `AWS` (or any vendor name) → subgraph.
- Nodes are **sized by criticality score** and **coloured by type**:
  - Purple = Vendor, Cyan = Service, Green = Contract, Red = DORAObligation
- Hover a node for tooltip (type, score, country).

### Gap Analysis tab

1. Fill in **Contract ID**, **Vendor name**, and paste the contract text (first 3000 chars minimum).
2. Optionally restrict to specific obligations (e.g. `DORA-Art30-2-a, DORA-Art30-2-b`).
3. Click **Run Gap Analysis** — takes 60–180 s (12 sequential LLM calls).
4. Results appear inline: findings with verdict badges (met / partial / unmet),
   evidence quotes, and remediation proposals with EU-sovereign alternatives.

### Report tab

- Paste a **Session ID** (shown after gap analysis or in Sessions tab).
- **JSON** button → full `ReportArtifact` JSON.
- **Markdown** button → formatted audit report, copyable.

### Sessions tab

Lists every gap analysis run with risk level and obligation counts.
Click **View** to jump directly to its report.

### Jobs tab

Lists every ingest job with status (running / done / error), vendor name, and score.
Useful for debugging failed uploads.

---

## 9. API reference

Full interactive docs at **http://localhost:8000/docs**.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check — Neo4j, keys, VS |
| `POST` | `/api/ingest/dora?force=false` | Seed DORA regulation (idempotent) |
| `POST` | `/api/ingest?contract_id=X` | Upload contract PDF → `{job_id}` |
| `GET` | `/api/jobs/{job_id}` | Poll pipeline job status |
| `GET` | `/api/jobs` | List all jobs |
| `GET` | `/api/graph?root_vendor=AWS&depth=2` | Sigma.js graph JSON |
| `GET` | `/api/graph/concentration` | Vendors by criticality score |
| `POST` | `/api/gap-analysis` | Run DORA gap analysis |
| `POST` | `/api/remediation` | Re-run remediation for a session |
| `GET` | `/api/report/{session_id}` | JSON report |
| `GET` | `/api/report/{session_id}/markdown` | Markdown report |
| `GET` | `/api/sessions` | List all sessions |
| `GET` | `/api/sessions/{id}/trace` | Full report for session |

### Example: upload a contract

```bash
curl -X POST http://localhost:8000/api/ingest \
  -F "file=@contract.pdf" \
  -F "contract_id=my-contract-001"
# → {"job_id": "a1b2c3d4", "status": "running", "contract_id": "my-contract-001"}

# Poll until done
curl http://localhost:8000/api/jobs/a1b2c3d4
# → {"status": "done", "result": {"vendor_name": "AWS", "criticality_score": 0.45, ...}}
```

### Example: gap analysis

```bash
curl -X POST http://localhost:8000/api/gap-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "contract_ids": ["my-contract-001"],
    "vendor_name": "AWS",
    "contract_text_preview": "1. SCOPE OF SERVICES\nAWS shall provide...",
    "obligation_ids": ["DORA-Art30-2-a", "DORA-Art30-2-b"]
  }'
```

---

## 10. Running tests

```bash
# Unit tests (no external deps — always fast)
uv run pytest tests/unit/ -v          # 49 tests

# Smoke test (needs live Cerebras + Gemini + VS)
make smoke

# Full pipeline integration test (needs all deps + Neo4j)
make pipeline
```

---

## 11. Makefile targets

```
make dev           Start API server with hot-reload
make test          Run all tests
make test-unit     Unit tests only
make smoke         LLM + embeddings + RAG smoke test
make pipeline      Full 6-step integration test
make neo4j-up      Start Neo4j in Docker
make neo4j-down    Stop Neo4j
make seed-dora     Index DORA regulation into Vector Search
make seed-demo     Ingest demo AWS contract (full pipeline)
make reset-graph   Wipe Neo4j + re-apply schema
make lint          ruff check
make fmt           ruff format
```

---

## 12. Project structure

```
app/
├── main.py                    # FastAPI app + lifespan (startup)
├── config.py                  # All settings (pydantic-settings, reads .env)
├── deps.py                    # FastAPI dependency providers
├── jobs.py                    # In-memory ingest job store
├── sessions.py                # In-memory session/report store
├── agents/
│   ├── ingestion.py           # ContractIngestionWorkflow (4 steps)
│   ├── extraction.py          # ExtractionAgent: contract text → ContractExtraction
│   ├── graph_builder.py       # GraphBuilderAgent: upserts into Neo4j
│   ├── risk_scorer.py         # RiskScorer: recomputes criticality_score
│   ├── gap_analysis.py        # GapAnalysisAgent: 12 DORA obligations → findings
│   ├── remediation.py         # RemediationAgent: findings → EU alternatives
│   ├── report_assembler.py    # ReportAssembler: findings + proposals → report
│   └── events.py              # LlamaIndex Workflow event types
├── api/
│   ├── ingest.py              # POST /api/ingest (async job)
│   ├── graph.py               # GET /api/graph
│   ├── analysis.py            # POST /api/gap-analysis
│   ├── remediation.py         # POST /api/remediation
│   ├── report.py              # GET /api/report/{id}
│   └── sessions.py            # GET /api/sessions
├── graph/
│   ├── client.py              # run_read / run_write wrappers
│   ├── schema.py              # Cypher constraints + indexes
│   ├── upsert.py              # Idempotent MERGE statements
│   ├── queries.py             # Graph read queries (Sigma.js shapes)
│   └── resolver.py            # Entity resolution (fuzzy vendor dedup)
├── llm/
│   ├── client.py              # make_llm() — Cerebras via OpenAILike
│   ├── embeddings.py          # make_embed_model() — Gemini Embedding 2
│   └── retry.py               # chat_with_retry() — exponential backoff on 429
├── rag/
│   ├── store.py               # Vertex AI VS v2 collection setup
│   ├── ingestion_pipeline.py  # PDF → chunks → embed → VS
│   └── citation_query.py      # CitationQueryEngine wrapper
├── schemas/                   # Pydantic models (single source of truth)
│   ├── contract.py            # ContractExtraction, EvidenceSpan, ServiceClause
│   ├── obligation.py          # ObligationFinding, Verdict
│   ├── graph.py               # GraphNode, GraphEdge, GraphResponse
│   ├── remediation.py         # RemediationProposal, AlternativeVendor
│   └── report.py              # ReportArtifact
├── data/
│   ├── dora_obligations.yaml  # 12 DORA Art.30 obligations (ground truth)
│   └── sovereign_alternatives.yaml  # EU sovereign alternatives per vendor
├── static/
│   └── index.html             # Test UI (vanilla JS + vis.js)
└── tracing/
    └── logger.py              # structlog JSON configuration

scripts/
├── seed_dora.py               # Download + index DORA PDF
├── seed_demo_contracts.py     # Ingest demo AWS contract (full pipeline)
├── reset_neo4j.py             # Wipe graph + re-apply schema
├── test_smoke.py              # Quick LLM/embed/RAG sanity check
└── test_pipeline.py           # End-to-end 6-step integration test

tests/
├── unit/                      # 49 fast tests, no external deps
└── fixtures/
    ├── dora_regulation.pdf    # DORA EU 2022/2554 (downloaded by seed_dora.py)
    └── demo_aws_contract.txt  # Fictitious AWS contract for demo
```

---

## 13. Key data models

### ContractExtraction (output of ExtractionAgent)
```python
ContractExtraction(
    contract_id="my-contract-001",
    vendor_name="Amazon Web Services EMEA SARL",
    vendor_country="LU",
    services=[ServiceClause(service_name="Amazon EC2", sla_hours=4.0)],
    covered_obligation_ids=["DORA-Art30-2-a", "DORA-Art30-2-b"],
    evidence_spans=[EvidenceSpan(text="All data stored in EU regions", page=3, ...)],
    sub_vendors=["Equinix", "Lumen Technologies"],
)
```

### ObligationFinding (output of GapAnalysisAgent)
```python
ObligationFinding(
    obligation_id="DORA-Art30-2-b",
    article="30", paragraph="2b",
    verdict=Verdict.PARTIALLY_MET,
    rationale="Clause 3 names EU regions but lacks change notification.",
    gap_description="Missing notification obligation for location changes.",
    risk_level="high",
    evidence_spans=[...],
)
```

### Neo4j graph schema
```
(:Vendor)          -[:PROVIDES]->   (:Service)
(:Contract)        -[:COVERS]->     (:Vendor)
(:Contract)        -[:EVIDENCES]->  (:DORAObligation)
(:Vendor)          -[:DEPENDS_ON]-> (:Vendor)   # 4th-party chains
```

Node properties on `:Vendor`:
- `criticality_score` ∈ [0, 1] — drives node size in graph
- Computed from: `contracts×0.3 + services×0.3 + dependents×0.2 + country_risk×0.2`

---

## 14. Common issues

### `make dev` fails at startup

```
Error: neo4j connection refused
```
→ Run `make neo4j-up` and wait 10 s for Neo4j to initialise.

```
Error: google.auth.exceptions.DefaultCredentialsError
```
→ Run `gcloud auth application-default login`.

```
Error: 403 PERMISSION_DENIED on Vertex AI
```
→ Billing not enabled. Run: `gcloud billing projects link PROJECT_ID --billing-account=ACCOUNT_ID`

### Ingest job stays `running` forever

Check `GET /api/jobs/{job_id}` — if status is `error`, the `error` field has the message.
Common causes:
- Cerebras 429 (rate limit) — retry waits up to 5 min automatically
- Vertex AI quota exceeded — wait and retry
- PDF is scanned/image-only — PyMuPDF extracts no text; use LlamaParse

### Graph is empty after ingest

The graph is only populated by the full `ContractIngestionWorkflow`.
If you ingested via a direct `POST /api/ingest/dora` call, it skips extraction/graph.
Use `POST /api/ingest` with a vendor contract PDF instead.

### Gap analysis returns all `unknown` verdicts

The LLM parse failed silently. Check logs for `gap_analysis_json_failed`.
Paste more contract text in `contract_text_preview` (aim for 2000+ chars covering key clauses).

### `password123` in docker-compose / .env.example

Both are local-dev defaults only. Change `NEO4J_PASSWORD` in `.env` and in the
`docker-compose.yml` `NEO4J_AUTH` line if you expose Neo4j outside localhost.

---

## 15. Cerebras model limits

| Model | Context | RPM | Best for |
|-------|---------|-----|---------|
| `llama3.1-8b` | 8 192 | 100 | Gap analysis (12 calls/run), remediation, reports |
| `qwen-3-235b-a22b-instruct-2507` | 65 536 | 5 | Not currently used — 429s under load |

The app uses `llama3.1-8b` for everything. Contract text is truncated to 6 000 chars
for extraction. To switch models, set `CEREBRAS_MODEL=<model>` in `.env`.
