# DORA AI Analyst — Agent Handoff Report

**Date:** 2026-04-25  
**Repo root:** `/home/kepard/dev/hec-hackathon`  
**Stack:** Python 3.14, FastAPI, LlamaIndex Workflows, Cerebras inference, Gemini Embedding 2, Vertex AI Vector Search v2, Neo4j, Google Cloud Storage  
**Package manager:** `uv` (`uv run <cmd>` for everything)

---

## Security Status

### .env committed in git history — PARTIALLY
| Commit | Content |
|--------|---------|
| `b10f67f` (first commit) | `.env` was committed with **placeholder** values for API keys (`test-key-placeholder`) but with a real `GCP_PROJECT=gen-lang-client-0704112831` and `NEO4J_PASSWORD=password123` |
| `c66e6e5` | `.env` was removed from tracking (`git rm --cached .env`) |

**Current state:** `.env` is in `.gitignore` and is NOT tracked. The real Cerebras and Gemini API keys (`csk-*`, `AIzaSy*`) were **never committed**.

**What IS in git history:**
- `GCP_PROJECT=gen-lang-client-0704112831` — GCP project ID (not a secret, but sensitive)
- `NEO4J_PASSWORD=password123` — also present in `docker-compose.yml` and `.env.example` (local dev only, explicitly commented as such)

**Action required before pushing to GitHub:**
```bash
# Remove the first commit's .env from history entirely
git filter-repo --path .env --invert-paths
# Or use BFG Cleaner
```
If this repo stays private/local only, the risk is low. Do NOT push to a public remote without cleaning history first.

**Currently tracked files with `password123`:**
- `docker-compose.yml` line 8 — comment says "local dev only"
- `.env.example` line 24 — example file, expected

---

## What Is Implemented

### Infrastructure
| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI app (`app/main.py`) | ✅ | Lifespan startup: Neo4j + LLM + embeddings + VS + workflow |
| Pydantic settings (`app/config.py`) | ✅ | All secrets via `.env`, validated at startup |
| structlog JSON logging | ✅ | `app/tracing/logger.py` |
| Docker Compose (Neo4j) | ✅ | `make neo4j-up` |
| Makefile | ✅ | `dev`, `test`, `smoke`, `pipeline`, `seed-dora`, `seed-demo`, `reset-graph` |

### LLM Layer
| Component | Status | Notes |
|-----------|--------|-------|
| Cerebras LLM client | ✅ | `app/llm/client.py` — OpenAILike adapter, model `llama3.1-8b` |
| Gemini Embedding 2 | ✅ | `app/llm/embeddings.py` — 768-dim MRL via `output_dimensionality` |
| Retry with backoff | ✅ | `app/llm/retry.py` — exponential backoff 4s→60s, 5 attempts on 429 |

### RAG Layer
| Component | Status | Notes |
|-----------|--------|-------|
| Vertex AI Vector Search v2 | ✅ | `app/rag/store.py` — collection `dora-analyst-docs`, region `us-central1` |
| PDF ingestion pipeline | ✅ | `app/rag/ingestion_pipeline.py` — PyMuPDF → SentenceSplitter(512/64) → embed → VS |
| CitationQueryEngine | ✅ | `app/rag/citation_query.py` — every answer cites source chunks |
| DORA regulation indexed | ✅ | 178 chunks from EU 2022/2554 PDF |

### AI Agents (LlamaIndex Workflows)
| Agent | File | Status | What it does |
|-------|------|--------|--------------|
| ContractIngestionWorkflow | `app/agents/ingestion.py` | ✅ | 4-step: parse_and_index → extract → build_graph → score_risks |
| ExtractionAgent | `app/agents/extraction.py` | ✅ | Contract text → `ContractExtraction` (JSON-mode, retry on parse fail) |
| GraphBuilderAgent | `app/agents/graph_builder.py` | ✅ | ContractExtraction → Neo4j MERGE upserts with entity resolution |
| RiskScorer | `app/agents/risk_scorer.py` | ✅ | Recomputes `criticality_score` after each ingest |
| GapAnalysisAgent | `app/agents/gap_analysis.py` | ✅ | 12 DORA Art.30 obligations → ObligationFinding with verdict + evidence |
| RemediationAgent | `app/agents/remediation.py` | ✅ | Fuzzy-match vendor → YAML alternatives → LLM remediation plan |
| ReportAssembler | `app/agents/report_assembler.py` | ✅ | Findings + proposals → ReportArtifact with LLM executive summary |

### Neo4j Graph Layer
| Component | Status | Notes |
|-----------|--------|-------|
| Schema (constraints + indexes) | ✅ | `app/graph/schema.py` — applied at startup |
| Upsert (idempotent MERGE) | ✅ | `app/graph/upsert.py` — Vendor, Service, Contract, DORAObligation, edges |
| Read queries | ✅ | `app/graph/queries.py` — full/subgraph + concentration ranking |
| Entity resolution | ✅ | `app/graph/resolver.py` — exact + rapidfuzz token_sort_ratio ≥ 90 |
| Graph schema (node types) | ✅ | Vendor, Service, BusinessFunction, Contract, DORAObligation |
| Edge types | ✅ | PROVIDES, COVERS, EVIDENCES, DEPENDS_ON |

### API Endpoints
| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/` | ✅ | Serves test UI (`app/static/index.html`) |
| GET | `/health` | ✅ | Neo4j + key + VS checks |
| POST | `/api/ingest/dora` | ✅ | Seed DORA regulation (idempotent) |
| POST | `/api/ingest` | ✅ | Upload contract → async job (returns `job_id`) |
| GET | `/api/jobs/{job_id}` | ✅ | Poll pipeline job status |
| GET | `/api/jobs` | ✅ | List all jobs |
| GET | `/api/graph` | ✅ | Sigma.js-compatible graph JSON |
| GET | `/api/graph/concentration` | ✅ | Vendor criticality ranking |
| POST | `/api/gap-analysis` | ✅ | Full analysis → ReportArtifact |
| POST | `/api/remediation` | ✅ | Re-run remediation for a session |
| GET | `/api/report/{session_id}` | ✅ | JSON report |
| GET | `/api/report/{session_id}/markdown` | ✅ | Markdown report |
| GET | `/api/sessions` | ✅ | List all sessions |
| GET | `/api/sessions/{session_id}` | ✅ | Session metadata |
| GET | `/api/sessions/{session_id}/trace` | ✅ | Full report for session |

### Data / Knowledge Base
| File | Status | Notes |
|------|--------|-------|
| `app/data/dora_obligations.yaml` | ✅ | 12 DORA Art.30 obligations (2a–2e, 3a–3g) |
| `app/data/sovereign_alternatives.yaml` | ✅ | 7 vendors with EU sovereign alternatives (AWS→OVHcloud/Scaleway, Azure→Whaller, etc.) |
| `tests/fixtures/dora_regulation.pdf` | ✅ | Full DORA EU 2022/2554 PDF (178 chunks indexed) |
| `tests/fixtures/demo_aws_contract.txt` | ✅ | Demo fixture AWS EMEA contract |

### Pydantic Schemas (`app/schemas/`)
All inter-layer contracts defined as Pydantic models:
- `ContractExtraction`, `EvidenceSpan`, `ServiceClause`
- `ObligationFinding`, `Verdict` (enum)
- `GraphNode`, `GraphEdge`, `GraphResponse` (Sigma.js shapes)
- `RemediationProposal`, `AlternativeVendor`
- `ReportArtifact`

### Test UI (`app/static/index.html`)
Single-file vanilla JS + vis.js frontend at `http://localhost:8000`:
- **Status tab**: health check, session state
- **Ingest tab**: seed DORA, upload contract (polls job until done), concentration ranking
- **Graph tab**: vis.js Network — nodes coloured by type, sized by `criticality_score`
- **Gap Analysis tab**: full form → live findings + remediation cards with EU alternatives
- **Report tab**: JSON + Markdown export
- **Sessions tab**: list all analyses with risk badge, one-click to report
- **Jobs tab**: all ingest jobs with status/vendor/score

### Tests (49 unit tests, all passing)
```
tests/unit/test_schemas.py          7 tests
tests/unit/test_resolver.py         5 tests
tests/unit/test_extraction.py       8 tests
tests/unit/test_risk_scorer.py      5 tests
tests/unit/test_gap_analysis.py     5 tests
tests/unit/test_remediation.py      6 tests
tests/unit/test_report.py           5 tests
tests/unit/test_obligations_yaml.py 4 tests
tests/unit/test_sovereign_yaml.py   4 tests
```

Run with: `uv run pytest tests/unit/ -v`

---

## What Is Missing / Not Yet Implemented

### High Priority (breaks demo or correctness)

#### 1. Persistence (in-memory only — lost on restart)
**Files:** `app/api/report.py` (`_reports` dict), `app/sessions.py` (`_sessions` dict), `app/jobs.py` (`_jobs` dict)  
**Problem:** All session data, reports, and job results are lost when the server restarts. For a live demo this is fine. For production or multi-instance deployment, this is a blocker.  
**Fix:** Persist to Neo4j or GCS. Simplest approach: serialize `ReportArtifact` as JSON to `GCS_BUCKET/reports/{session_id}.json` on write; read back on GET.

#### 2. Gap analysis does not filter RAG by contract
**File:** `app/agents/gap_analysis.py`, function `_evaluate_one`  
**Problem:** The `CitationQueryEngine` queries the entire Vector Store (DORA + all contracts). It may return DORA text instead of contract text when searching for obligation evidence. The contract text preview (3000 chars) is passed directly but is truncated for long contracts.  
**Fix options:**
- A) Store the full extracted contract text in Neo4j on the `Contract` node and retrieve it here
- B) Add a metadata filter to Vertex AI VS queries (filter by `doc_type=contract AND contract_id=$id`)
- C) Use a separate CitationQueryEngine per contract with a metadata filter — cleanest but requires LlamaIndex `MetadataFilter` support on Vertex AI VS v2

#### 3. Context window for llama3.1-8b (8 192 tokens) limits analysis accuracy
**Problem:** Real contracts can be 50-200 pages. We truncate to 6 000 chars (~1 500 tokens), missing most of the document. The gap analysis may miss clauses that appear later in the contract.  
**Fix:** See model recommendation section below.

#### 4. LlamaParse not implemented
**File:** `app/rag/ingestion_pipeline.py` line 31  
**Problem:** `_parse_pdf_llamaparse` raises `NotImplementedError`. PyMuPDF works for most PDFs but fails on scanned documents, complex tables, and multi-column layouts common in legal contracts.  
**Fix:** Implement async LlamaParse call with `LlamaParse(api_key=..., result_type="markdown")`. Key is in `.env` as `LLAMA_PARSE_API_KEY` (optional).

#### 5. No `vendor_aliases.yaml` escape hatch
**File:** `app/graph/resolver.py`  
**Problem:** Entity resolution relies on fuzzy matching alone. "Amazon", "AWS", "AMZN", "Amazon EMEA" may not all resolve to the same node. The PLAN mentioned a `vendor_aliases.yaml` canonical file as an escape hatch.  
**Fix:** Create `app/data/vendor_aliases.yaml` with known aliases per canonical name. Load it in `resolver.py` before fuzzy matching.

### Medium Priority (polish / production-readiness)

#### 6. No `BusinessFunction` nodes populated
**Problem:** The graph schema includes `BusinessFunction` nodes (e.g. "Payments", "Risk Management") that show which teams are affected if a vendor goes down. No agent creates them. The PLAN described linking vendors to business functions for blast-radius analysis.  
**Fix:** Add a `BusinessFunctionExtractor` step in the ingestion workflow that infers impacted business functions from the contract service description.

#### 7. No graph centrality / PageRank computation
**File:** `app/agents/risk_scorer.py`  
**Problem:** The current `criticality_score` is a simple weighted formula (contracts + services + dependents + country). Neo4j Graph Data Science (GDS) PageRank or betweenness centrality would be more accurate for concentration risk.  
**Fix:** Install `neo4j-graph-data-science` Python client; call `gds.pageRank.stream` after each ingest. Only feasible if using Neo4j Enterprise or AuraDB (GDS available).

#### 8. `POST /api/ingest` accepts only PDF
**Problem:** The demo fixture `demo_aws_contract.txt` is a `.txt` file. The seed script converts it to PDF with PyMuPDF. The API rejects non-PDF content types.  
**Fix:** Add `text/plain` to the accepted content types; handle text files without parsing step.

#### 9. No authentication / API key guard
**Problem:** All endpoints are public. For a B2B on-prem deployment, at minimum a static bearer token or OAuth2 is needed.  
**Fix:** Add FastAPI `HTTPBearer` dependency with a token from settings. Do not implement until the frontend is ready (it needs to pass the token).

#### 10. Report export formats
**Problem:** Only JSON and Markdown. Legal/compliance teams need PDF reports.  
**Fix:** Use `weasyprint` or `reportlab` to render the Markdown to PDF server-side. Add `GET /api/report/{session_id}/pdf`.

#### 11. Sovereign alternatives YAML is incomplete
**File:** `app/data/sovereign_alternatives.yaml`  
**Problem:** 7 vendors covered (AWS, Azure, Google Cloud, Cloudflare, Okta, Twilio, GitHub). Many common ICT third parties missing (Salesforce, SAP, Oracle, ServiceNow, etc.).  
**Fix:** Expand YAML with 20-30 more vendors. Structured data, no LLM needed.

#### 12. No rate-limit guard on gap analysis (12 LLM calls per run)
**Problem:** `run_gap_analysis` calls `chat_with_retry` 12 times sequentially (one per obligation). With llama3.1-8b at 100 RPM this is fine. With qwen at 5 RPM, 12 calls would take 2+ minutes of wait time minimum.  
**Fix:** If using qwen, add `asyncio.sleep(12)` between calls or batch obligations. If staying on llama3.1-8b, no change needed.

---

## Model Recommendation: llama3.1-8b vs qwen-3-235b

### Quotas summary
| Model | Context | RPM | TPM |
|-------|---------|-----|-----|
| `llama3.1-8b` | 8 192 | 100 | 100 000 |
| `qwen-3-235b-a22b-instruct-2507` | 65 536 | 5 | 30 000 |

### Usage analysis per pipeline run
| Operation | LLM calls | Tokens/call (est.) | Fits llama? | Fits qwen? |
|-----------|-----------|-------------------|-------------|------------|
| Extraction | 1 | ~2 000 | ✅ | ✅ |
| Gap analysis (12 obligations) | 12 | ~1 500 | ✅ | ⚠️ needs 2.4 min wait |
| Remediation (per unmet finding) | 3–8 | ~800 | ✅ | ⚠️ RPM exhausted |
| Report assembly | 1 | ~600 | ✅ | ✅ |
| **Total per full run** | **~20** | — | ✅ 12 s | ❌ 4+ min |

### Recommendation: **Keep llama3.1-8b as default. Use qwen only for extraction.**

**Rationale:**
- Gap analysis makes 12 sequential LLM calls. At qwen's 5 RPM limit, a single full-analysis run takes **at minimum 2.4 minutes** purely due to rate limiting, independent of model quality. This makes qwen unsuitable for gap analysis in a demo context.
- llama3.1-8b handles the full pipeline in ~30–60 seconds total with no rate-limit pressure (100 RPM).
- The 8 192-token context IS a real constraint for extraction (long contracts get truncated to 6 000 chars). This is where qwen's 65k context would genuinely help.

**Optimal approach (two-model strategy):**
1. Use `llama3.1-8b` for gap analysis, remediation, and report assembly (many calls, low token needs).
2. Use `qwen-3-235b` for extraction only (1 call per contract, full contract text fits in 65k context — no truncation, better clause extraction).

**Implementation:** Add `extraction_model` config field in `app/config.py` (defaults to qwen); `analysis_model` defaults to llama. Pass the right model to each agent in `ingestion.py`.

---

## Running the Project

```bash
# Prerequisites: Neo4j running, GCP credentials configured
make neo4j-up        # start Neo4j (Docker required)
make seed-dora       # index DORA regulation into Vertex AI VS
make seed-demo       # ingest demo AWS contract through full pipeline
make dev             # start FastAPI at http://localhost:8000

# Testing
uv run pytest tests/unit/ -v    # 49 unit tests
make smoke                       # LLM + embeddings + RAG smoke test
make pipeline                    # full 6-step integration test

# Utilities
make reset-graph                 # wipe Neo4j and re-apply schema
```

---

## Key Files for Next Agent

| File | Purpose |
|------|---------|
| `PLAN.md` | Original 470-line architecture plan |
| `app/config.py` | All settings — start here |
| `app/main.py` | FastAPI lifespan — all state attached to `app.state` |
| `app/agents/ingestion.py` | Workflow orchestration — entry point for contract pipeline |
| `app/agents/gap_analysis.py` | Core DORA analysis loop — most important agent |
| `app/data/dora_obligations.yaml` | 12 DORA Art.30 obligations — ground truth for gap analysis |
| `app/data/sovereign_alternatives.yaml` | EU sovereign alternatives knowledge base |
| `app/schemas/__init__.py` | All Pydantic models — read this before touching any agent |
| `app/graph/upsert.py` | Neo4j write operations — entity relationships |
| `app/static/index.html` | Test frontend — single file, vanilla JS |
| `.env.example` | All required environment variables with descriptions |
