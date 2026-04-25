# DORA AI Analyst — MVP Implementation Plan

> **Tagline:** *The AI analyst for DORA, not another compliance dashboard.*
>
> Status: planning (no code written). Plan assumes a hackathon-weekend MVP that pitches in 3 minutes with a working demo. Last updated 2026-04-25.

---

## 1. Positioning & Differentiators

The market is crowded with control-mapping SaaS (DORA360, Vanta, Sprinto, Regulativ.ai, ROK Solution, ProcessUnity, Formalize, Scrut). Their UX is a checklist-with-status. Our wedge is fundamentally different on three axes:

| Axis | Competitors | Us |
|---|---|---|
| **Reasoning** | Pre-mapped controls, manual evidence upload | LLM agents that read the contract, extract evidence, and *explain* why an obligation is met/partial/missing — with verbatim citations |
| **Risk modeling** | Vendor list + spreadsheet | Live dependency graph (Neo4j) — concentration, 4th-party chains, blast radius per business function |
| **Remediation** | "You're non-compliant, fix it" | Prioritized remediation with **sovereign EU alternatives**, cost delta, feature delta |

Three sentences for the pitch:
1. DORA fines hit 1% of global daily revenue for critical ICT providers; banks face GDPR-scale penalties.
2. Existing tools turn DORA into a checklist — we turn it into an analyst.
3. Upload your contracts; we extract obligations, map dependencies, find gaps with sources, and propose sovereign alternatives.

---

## 2. Scope

### In-scope for MVP demo
1. **Ingest**: drop 2-3 vendor contracts (PDF) into the system; DORA regulation pre-loaded.
2. **Analyze**: agents extract structured contract data with source spans.
3. **Graph**: Neo4j populated with vendor / service / business-function / contract / obligation nodes; Sigma.js-ready JSON endpoint.
4. **Gap analysis**: 8-12 DORA Article 30 contractual obligations evaluated per contract (`met` / `partially_met` / `not_met` / `weak_evidence`) — each finding cites the exact contract span.
5. **Remediation**: for each gap or critical-vendor concentration, propose 1-2 sovereign EU alternatives with rough cost / feature delta.
6. **Report**: assembled audit document (Markdown + JSON) with full citation trail.
7. **API**: FastAPI surface (no frontend this iteration — Sigma.js consumes JSON later).

### Explicitly out of scope (post-MVP, marked `#TODO` in code)
- Frontend (Next.js + Sigma.js graph view, planned next iteration)
- Auth (no auth — single-user demo)
- Agent action traceability UI (log structured events to disk now, render later — like Rippletide)
- On-prem deployment (Vertex AI for MVP, Neo4j on GCP aswell)
- DORA Pillars 1-3, 5 (we focus on Pillar 4: ICT Third-Party Risk for the demo wedge)
- Full DORA Register of Information (RoI) export
- Multi-tenant isolation, RBAC
- Continuous monitoring / scheduled re-runs
- Incident reporting workflows

### Decision boundaries (do not violate without re-planning)
- **No mocked features.** If a slice isn't done, it gets a `#TODO` and the endpoint returns 501 — never fake data.
- **No premature abstraction.** Single concrete implementation; abstract only when a swap is actually needed.
- **Cite or don't claim.** Any agent assertion about a contract or obligation must carry source spans (page, char range, quoted text).

---

## 3. Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                         FastAPI (uvicorn)                              │
│  /ingest  /graph  /gap-analysis  /remediation  /report  /sessions/:id │
└──────┬──────────────┬───────────────┬──────────────┬─────────────────┘
       │              │               │              │
       ▼              ▼               ▼              ▼
  ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌────────────┐
  │Ingestion│   │Extraction│   │   Graph  │   │GapAnalysis │
  │ Workflow│──▶│  Agent   │──▶│  Builder │──▶│   Agent    │
  └────┬────┘   └────┬─────┘   └────┬─────┘   └──────┬─────┘
       │             │              │                │
       ▼             ▼              ▼                ▼
  ┌─────────┐  ┌──────────┐   ┌──────────┐   ┌────────────┐
  │GCS PDFs │  │ Vertex AI│   │  Neo4j   │   │CitationRAG │
  │         │  │  Vector  │   │  (graph) │   │  (LIDX)    │
  │         │  │  Search  │   │          │   │            │
  └─────────┘  └──────────┘   └──────────┘   └────────────┘
                                                    │
                                                    ▼
                                            ┌──────────────┐
                                            │ Remediation  │
                                            │    Agent     │
                                            └──────┬───────┘
                                                   ▼
                                            ┌──────────────┐
                                            │   Report     │
                                            │   Assembler  │
                                            └──────────────┘
```

**Data flow per ingestion**:
1. PDF arrives → uploaded to GCS → parsed (LlamaParse or PyMuPDF fallback) → chunked → embedded via Gemini Embedding → indexed in Vertex AI Vector Search.
2. ExtractionAgent runs against the parsed doc, emits `ContractExtraction` Pydantic object with cited spans.
3. GraphBuilder upserts nodes/edges into Neo4j (with entity resolution) (Neo4j AuraDB on GCP Marketplace).
4. RiskScorer recomputes node weights (centrality, concentration).

**Data flow per analysis run**:
1. GapAnalysisAgent iterates the DORA obligation subset; for each, retrieves contract chunks + DORA chunks via `CitationQueryEngine`; LLM emits a `ObligationFinding`.
2. RemediationAgent reads `ObligationFinding` list + critical-vendor list from graph; proposes alternatives.
3. ReportAssembler emits Markdown + JSON.

---

## 4. Tech Stack

| Layer              | Choice                                                                                                                                 | Version (verified 2026-04-25)                                            | Rationale                                                                              |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| Python             | 3.13                                                                                                                                   | 3.13.x                                                                   | User choice                                                                            |
| Package mgr        | `uv`                                                                                                                                   | latest                                                                   | User choice                                                                            |
| API                | FastAPI + uvicorn                                                                                                                      | latest                                                                   | User choice                                                                            |
| Agent orch         | `llama-index-workflows` (event-driven, async-first; also exported via `llama_index.core.workflow`)                                     | latest stable (Feb 28 2026 release)                                      | User choice                                                                            |
| RAG framework      | `llama-index`                                                                                                                          | latest stable                                                            | User choice                                                                            |
| LLM                | Z.ai `glm-4.7` via OpenAI-compatible endpoint (https://api.cerebras.ai/v1/chat/completions)`                                           | API key auth                                                             | User choice; 200K context; supports tool calling                                       |
| LLM client adapter | `llama-index-llms-openai-like`                                                                                                         | latest                                                                   | Lets us swap providers later via env (Cerebras, OpenAI, Anthropic) without code change |
| Embeddings         | Gemini Embedding 2 (`gemini-embedding-2`, GA via Vertex AI; 3072-dim default with Matryoshka — we'll use 768 for storage/cost balance) | latest                                                                   | User choice                                                                            |
| Vector store       | Vertex AI Vector Search v2.0 (collection-based)                                                                                        | LlamaIndex integration: `llama-index-vector-stores-vertexaivectorsearch` | User choice; SEMANTIC_HYBRID supported                                                 |
| Graph DB           | Neo4j (managed: AuraDB on GCP marketplace)                                                                                             | Python driver `neo4j` latest                                             | User choice                                                                            |
| Doc storage        | GCS bucket                                                                                                                             | `google-cloud-storage` latest                                            | User choice                                                                            |
| PDF parser         | LlamaParse (primary, handles tables) → PyMuPDF (`pymupdf`) fallback                                                                    | latest                                                                   | LlamaParse for fidelity, PyMuPDF for offline/no-key paths                              |
| Schemas            | Pydantic v2                                                                                                                            | latest                                                                   | Pairs with FastAPI / LlamaIndex output parsers                                         |
| Logging            | `structlog` + JSON to disk                                                                                                             | latest                                                                   | Structured events feed future trace UI                                                 |
| Testing            | `pytest` + `pytest-asyncio`                                                                                                            | latest                                                                   | Required for workflow tests                                                            |
| Lint/format        | `ruff`                                                                                                                                 | latest                                                                   | Single-tool stack                                                                      |
| Env                | `pydantic-settings`                                                                                                                    | latest                                                                   | Twelve-factor config                                                                   |
| Container          | Docker + docker-compose (Neo4j only for local dev)                                                                                     | —                                                                        | —                                                                                      |
| Deploy             | Cloud Run (FastAPI) + Vertex AI Vector Search + Neo4j AuraDB                                                                           | GCP                                                                      | Post-demo deploy target                                                                |

**Versioning policy**: pin majors in `pyproject.toml`, allow minor/patch updates. Run `uv lock` for reproducibility. The implementing agent must `uv pip install --upgrade` and verify each package's CHANGELOG entry against the import surface used in code (LlamaIndex's vector store / workflow APIs have shifted between minor releases).

---

## 5. Repository Layout

```
hec-hackathon/
├── pyproject.toml                 # uv-managed deps
├── uv.lock
├── .env.example                   # all required env vars
├── docker-compose.yml             # local Neo4j + (optional) MinIO
├── README.md                      # quickstart
├── PLAN.md                        # this file
├── Makefile                       # `make dev`, `make test`, `make ingest-demo`
│
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app factory + router mounting
│   ├── config.py                  # Pydantic Settings (env-driven)
│   ├── deps.py                    # FastAPI dependency providers
│   │
│   ├── api/                       # HTTP layer (thin)
│   │   ├── __init__.py
│   │   ├── ingest.py              # POST /api/ingest
│   │   ├── graph.py               # GET /api/graph (Sigma.js JSON)
│   │   ├── analysis.py            # POST /api/gap-analysis
│   │   ├── remediation.py         # POST /api/remediation
│   │   ├── report.py              # GET /api/report/{client_id}
│   │   └── sessions.py            # GET /api/sessions/{id}/trace  [#TODO post-MVP]
│   │
│   ├── agents/                    # LlamaIndex Workflows
│   │   ├── __init__.py
│   │   ├── ingestion.py           # IngestionWorkflow
│   │   ├── extraction.py          # ExtractionAgent (contract → ContractExtraction)
│   │   ├── graph_builder.py       # GraphBuilderAgent (upsert + entity resolution)
│   │   ├── risk_scorer.py         # RiskScorer (graph metrics)
│   │   ├── gap_analysis.py        # GapAnalysisAgent (per obligation)
│   │   ├── remediation.py         # RemediationAgent (alternatives)
│   │   └── report_assembler.py    # ReportAssembler
│   │
│   ├── rag/                       # LlamaIndex index layer
│   │   ├── __init__.py
│   │   ├── store.py               # build vector store + index from settings
│   │   ├── citation_query.py      # CitationQueryEngine wrapper
│   │   └── ingestion_pipeline.py  # parse → chunk → embed → upsert
│   │
│   ├── graph/                     # Neo4j layer
│   │   ├── __init__.py
│   │   ├── client.py              # async neo4j.AsyncGraphDatabase wrapper
│   │   ├── schema.py              # Cypher constraints + indexes
│   │   ├── upsert.py              # idempotent MERGE statements
│   │   ├── queries.py             # read queries (centrality, concentration)
│   │   └── resolver.py            # entity resolution (fuzzy vendor name match)
│   │
│   ├── schemas/                   # Pydantic — single source of truth
│   │   ├── __init__.py
│   │   ├── contract.py            # ContractExtraction, ServiceClause, etc.
│   │   ├── obligation.py          # ObligationFinding, EvidenceSpan, Verdict
│   │   ├── graph.py               # GraphNode, GraphEdge (Sigma-compatible)
│   │   ├── remediation.py         # RemediationProposal, AlternativeVendor
│   │   └── report.py              # ReportArtifact
│   │
│   ├── llm/                       # LLM provider abstraction
│   │   ├── __init__.py
│   │   ├── client.py              # OpenAILike wrapper for Z.ai GLM-4.7
│   │   └── embeddings.py          # GeminiEmbedding wrapper
│   │
│   ├── data/                      # Static seed data (committed, demo-friendly)
│   │   ├── dora_obligations.yaml  # 8-12 Art-30 obligations, demo-ready
│   │   └── sovereign_alternatives.yaml  # EU alternatives knowledge base
│   │
│   └── tracing/                   # Structured event log
│       ├── __init__.py
│       └── logger.py              # structlog setup + JSON sink
│
├── tests/
│   ├── conftest.py                # async fixtures, Neo4j test container
│   ├── unit/
│   │   ├── test_schemas.py
│   │   ├── test_resolver.py       # entity resolution
│   │   └── test_obligations.py    # YAML loads & shape
│   ├── integration/
│   │   ├── test_ingestion.py      # parse → embed → index roundtrip
│   │   ├── test_graph_upsert.py   # against test Neo4j container
│   │   └── test_gap_analysis.py   # one obligation against fixture contract
│   └── fixtures/
│       ├── demo_contracts/        # 2-3 sample PDFs (committed)
│       └── dora_chunks.json       # pre-chunked DORA text for fast tests
│
└── scripts/
    ├── seed_dora.py               # one-shot: download/upload DORA, build index
    ├── seed_demo_contracts.py     # ingest fixture contracts end-to-end
    └── reset_neo4j.py             # wipe graph for fresh demo
```

**Layout rules**:
- API layer is thin. No business logic in `api/` — routes orchestrate calls into `agents/` / `rag/` / `graph/`.
- Schemas (`app/schemas/`) are the single contract between layers. Workflows return Pydantic objects; API serializes them.
- LLM provider lives behind one wrapper (`app/llm/client.py`) so swapping Z.ai → Cerebras → OpenAI is a config change.

---

## 6. Domain Model

### 6.1 Pydantic schemas (key shapes)

```python
# app/schemas/contract.py
class EvidenceSpan(BaseModel):
    document_id: str
    page: int
    char_start: int
    char_end: int
    quoted_text: str          # verbatim, ≤500 chars

class ServiceClause(BaseModel):
    service_name: str         # "EC2", "managed Postgres"
    description: str
    evidence: list[EvidenceSpan]

class ContractExtraction(BaseModel):
    contract_id: str
    vendor_name: str
    vendor_country: str | None
    is_ict_service: bool
    supports_critical_function: bool
    services: list[ServiceClause]
    business_functions_covered: list[str]
    subcontractors: list[str]                # 4th-party chain
    has_audit_right: bool
    has_termination_clause: bool
    has_exit_strategy: bool
    has_sla: bool
    data_locations: list[str]
    evidence_per_field: dict[str, list[EvidenceSpan]]   # field → spans

# app/schemas/obligation.py
class Verdict(str, Enum):
    MET = "met"
    PARTIALLY_MET = "partially_met"
    NOT_MET = "not_met"
    WEAK_EVIDENCE = "weak_evidence"

class ObligationFinding(BaseModel):
    obligation_id: str               # e.g. "DORA-Art30-2-a"
    obligation_text: str
    verdict: Verdict
    rationale: str                   # ≤300 chars, agent's explanation
    evidence: list[EvidenceSpan]     # may be empty if NOT_MET
    confidence: float                # 0.0–1.0
```

### 6.2 Neo4j graph schema

**Node labels**:
- `:Vendor` { id, name, country, is_critical_provider, criticality_score }
- `:Service` { id, name, category }              # EC2, Stripe, Snowflake
- `:BusinessFunction` { id, name, is_critical }   # "Trading", "KYC", "Payments"
- `:Team` { id, name }
- `:Contract` { id, gcs_uri, ingested_at, vendor_id }
- `:DORAObligation` { id, article, paragraph, text, pillar }
- `:Risk` { id, type, severity, computed_at }
- `:Country` { code, name, eu_member }

**Relationships** (directed):
- `(Vendor)-[:PROVIDES]->(Service)`
- `(Service)-[:SUPPORTS]->(BusinessFunction)`
- `(Team)-[:OWNS]->(BusinessFunction)`
- `(Contract)-[:COVERS]->(Vendor)`
- `(Contract)-[:EVIDENCES {strength, evidence_span_id}]->(DORAObligation)`
- `(Vendor)-[:LOCATED_IN]->(Country)`
- `(Vendor)-[:DEPENDS_ON {context}]->(Vendor)`     # 4th-party
- `(Risk)-[:AFFECTS]->(Vendor)`
- `(Risk)-[:AFFECTS]->(Service)`

**Computed node properties** (recomputed by `RiskScorer` after each ingest):
- `Vendor.criticality_score` = weighted sum of:
  - count of `BusinessFunction` reachable in 2 hops (concentration)
  - any reachable function with `is_critical=true` → multiplier
  - depth of `:DEPENDS_ON` chain (4th-party multiplier)
- Drives node size in Sigma.js render.

**Constraints / indexes** (in `app/graph/schema.py`, applied at startup):
- `CREATE CONSTRAINT vendor_id IF NOT EXISTS FOR (v:Vendor) REQUIRE v.id IS UNIQUE`
- ... same for all node labels
- `CREATE INDEX vendor_name IF NOT EXISTS FOR (v:Vendor) ON (v.name)`

**Idempotent upsert pattern**:
```cypher
MERGE (v:Vendor {id: $id})
ON CREATE SET v.created_at = timestamp(), v.name = $name, ...
ON MATCH  SET v.name = coalesce($name, v.name), v.updated_at = timestamp()
```

### 6.3 Sigma.js JSON shape (returned by `GET /api/graph`)

```json
{
  "nodes": [
    {"key": "vendor:aws", "attributes": {"label": "AWS", "size": 28, "color": "#ff4d4d", "type": "Vendor", "criticality_score": 0.92}}
  ],
  "edges": [
    {"key": "edge:1", "source": "vendor:aws", "target": "service:ec2", "attributes": {"label": "PROVIDES", "size": 2}}
  ]
}
```

This matches Sigma.js v3+ graph format directly (we'll use `graphology` shape on the frontend later).

---

## 7. Agent Workflow Design (LlamaIndex Workflows)

Workflows are event-driven. Each agent is a `Workflow` subclass with `@step`-decorated handlers. Composition is via `start_event` → custom `Event` types → `StopEvent`.

### 7.1 Top-level: `ContractIngestionWorkflow`

```
StartEvent(contract_pdf_uri)
  → @step parse_pdf → DocParsed(doc, full_text)
  → @step embed_and_index → Indexed(node_ids)            # writes to Vertex AI VS
  → @step extract → Extracted(ContractExtraction)        # ExtractionAgent
  → @step build_graph → GraphUpdated(node_ids, edge_ids) # GraphBuilderAgent
  → @step score_risks → StopEvent(IngestionResult)       # RiskScorer
```

### 7.2 `ExtractionAgent` (sub-workflow)

Strategy: prompt LLM with chunks of contract + structured-output instruction (using LlamaIndex's `LLMTextCompletionProgram` or `function_calling=True` if Z.ai's tool-calling proves stable; fallback: JSON mode + Pydantic validation with retry-on-parse-error).

For each field in `ContractExtraction`, the agent must:
1. Retrieve relevant chunks from RAG (filtered to `contract_id`).
2. Ask LLM to extract value AND quote source verbatim.
3. Validate quoted text exists in source doc (literal substring match, with whitespace normalization). If not, retry once; second failure → mark field as `null` with `confidence=0`.

### 7.3 `GraphBuilderAgent`

Input: `ContractExtraction`. Output: list of `(node_id, edge_id)` upserted.

Steps:
1. **Entity resolution**: for `vendor_name`, query existing `:Vendor` nodes; if cosine similarity > 0.85 (on Gemini embedding of name) OR fuzzy match > 0.9 (rapidfuzz), reuse. Else create.
2. Same for `Service`, `BusinessFunction`.
3. Upsert via Cypher (idempotent MERGE).
4. Emit `GraphUpdated` event.

Note: entity resolution is the load-bearing magic. If "AWS" and "Amazon Web Services" don't merge, the graph fragments and concentration risk is wrong. Test this hard.

### 7.4 `GapAnalysisAgent`

Input: `contract_id` (or "all contracts").

For each obligation in `dora_obligations.yaml` (subset, see §10):
1. Build a query: obligation text + relevant keywords.
2. Use `CitationQueryEngine` to retrieve top-k chunks across DORA + the contract (metadata filter).
3. LLM call with prompt template:
   ```
   Obligation: {text}
   Contract excerpts: {chunks_with_citations}
   DORA reference: {dora_chunks}
   Return ObligationFinding JSON. Verdict ∈ {met, partially_met, not_met, weak_evidence}.
   Cite each evidence span by its node_id.
   ```
4. Validate citations resolve. If verdict=`met` but `evidence=[]`, force re-prompt or downgrade to `weak_evidence`.

Output: `list[ObligationFinding]`.

### 7.5 `RemediationAgent`

Input: list of `ObligationFinding` with `verdict ∈ {not_met, partially_met}` + critical vendors from graph (criticality > threshold).

For each:
1. Determine remediation type (contract amendment vs. vendor replacement vs. process gap).
2. If vendor concentration > 0.6 OR vendor in non-EU jurisdiction → propose sovereign alternative from `sovereign_alternatives.yaml` (e.g. AWS → OVHcloud / Scaleway / Outscale; Microsoft 365 → Whaller / Tchap; Snowflake → Dremio on EU infra).
3. LLM augments with cost / feature delta (qualitative; quantitative as `#TODO`).

Output: `list[RemediationProposal]`.

### 7.6 `ReportAssembler`

Input: `ContractExtraction[]`, `ObligationFinding[]`, `RemediationProposal[]`, graph snapshot.

Output: `ReportArtifact` with:
- Executive summary (LLM-generated, ≤300 words)
- Vendor table with criticality scores
- Obligation findings table (grouped by verdict)
- Remediation roadmap (prioritized by severity × business impact)
- Citation appendix (every claim → source)

Renders to Markdown for human, JSON for machine.

### 7.7 Traceability (basic implementation)

Every `@step` handler emits a structured event via `structlog` with:
- `session_id` (uuid per top-level workflow run)
- `step_name`, `agent_name`
- `timestamp`, `duration_ms`
- `inputs_summary`, `outputs_summary` (truncated)
- `llm_calls` (count, total tokens)
- `retrievals` (queries + top-k node ids)

Sink: append-only JSONL file at `./traces/{session_id}.jsonl`. Endpoint `/api/sessions/{id}/trace` returns the file. Render as timeline in UI later (`#TODO`).

---

## 8. RAG Design

### 8.1 Ingestion pipeline

```
PDF → LlamaParse (or PyMuPDF fallback)
    → SentenceSplitter (chunk_size=512, overlap=64)
    → metadata: {document_id, document_type ∈ {DORA, contract},
                 contract_id?, page, char_start, char_end}
    → Gemini Embedding 2 (output_dimensionality=768)
    → Vertex AI Vector Search v2.0 (single collection, hybrid search enabled)
```

### 8.2 Citation Query Engine

LlamaIndex's `CitationQueryEngine` (per the docs URL the user shared) wraps a query engine and returns `Response` objects with `source_nodes` carrying `node_id` and `metadata`. We'll subclass to:
- Always return spans with full evidence metadata (doc_id, page, char range).
- Reject responses where `len(source_nodes) == 0` (force the agent to retrieve before answering).

### 8.3 Retrieval modes

- **Per-contract retrieval**: filter by `contract_id` metadata.
- **Per-obligation retrieval**: filter by `document_type=DORA` + obligation keywords.
- **Cross-doc retrieval**: no filter, used by gap analysis to find evidence in *any* contract.

Hybrid search (`SEMANTIC_HYBRID` mode in Vertex AI VS) is on by default — better recall on legal terminology.

---

## 9. API Surface

| Method | Path | Body / Query | Returns | Notes |
|---|---|---|---|---|
| `POST` | `/api/ingest` | multipart: `file`, `contract_id?` | `IngestionResult { contract_id, node_ids, vertex_ids, extraction_summary }` | Triggers `ContractIngestionWorkflow` |
| `POST` | `/api/ingest/dora` | (idempotent) | `{ chunks_indexed: N }` | One-shot bootstrap; refuses to run twice |
| `GET` | `/api/graph` | `?root_vendor=AWS&depth=2` | Sigma.js JSON | Falls through to full graph if no root |
| `POST` | `/api/gap-analysis` | `{ contract_ids: [..] }` | `{ findings: ObligationFinding[] }` | Synchronous for MVP (≤30s); async post-MVP |
| `POST` | `/api/remediation` | `{ findings: [..] }` | `{ proposals: RemediationProposal[] }` | |
| `GET` | `/api/report/{client_id}` | — | `ReportArtifact` (JSON) or `text/markdown` based on Accept | |
| `GET` | `/api/sessions/{id}/trace` | — | JSONL stream | `#TODO` SSE later |
| `GET` | `/health` | — | `{ status, vector_store, neo4j, llm }` | Pings each dep |

**Conventions**:
- All errors return `{ error: { code, message, request_id } }` with consistent shape.
- All long operations return immediately if `?async=true` and emit a `session_id` to poll. MVP runs sync; flag exists but defaults sync.
- OpenAPI auto-generated by FastAPI at `/docs`.

---

## 10. DORA Obligation Subset (Demo)

Focus: **Article 30 — Contractual Provisions**. These are checklist-like and demo cleanly because the agent must find specific clauses in the contract. Stored in `app/data/dora_obligations.yaml`:

| ID | Article | Obligation | Pass criteria |
|---|---|---|---|
| `DORA-Art30-2-a` | 30(2)(a) | Clear description of services | Service list with scope present |
| `DORA-Art30-2-b` | 30(2)(b) | Locations (regions, countries) where services are provided / data is processed | Locations explicitly named |
| `DORA-Art30-2-c` | 30(2)(c) | Provisions on data protection, integrity, availability | Clause references GDPR/security |
| `DORA-Art30-2-d` | 30(2)(d) | Service level agreements (SLAs) | Quantitative SLA (uptime %, RTO, RPO) |
| `DORA-Art30-2-e` | 30(2)(e) | Provider must assist in incident response | Clause on incident cooperation |
| `DORA-Art30-3-a` | 30(3)(a) | Right to monitor performance on ongoing basis | Audit / monitoring right named |
| `DORA-Art30-3-b` | 30(3)(b) | Right to access, inspect, and audit | Explicit audit rights |
| `DORA-Art30-3-c` | 30(3)(c) | Cooperation with competent authorities | Regulator access named |
| `DORA-Art30-3-d` | 30(3)(d) | Termination rights — incl. for unremedied breach | Explicit termination clause |
| `DORA-Art30-3-e` | 30(3)(e) | Exit strategies and transition periods | Exit plan present |
| `DORA-Art30-3-f` | 30(3)(f) | Subcontracting conditions | 4th-party clause present |
| `DORA-Art30-3-g` | 30(3)(g) | Insurance, business continuity, DR | BCP/DR named |

12 obligations is enough to show breadth without bloating runtime. Each is a YAML record with `id`, `article`, `paragraph`, `text` (verbatim from regulation), `keywords` (for retrieval), `pass_criteria` (LLM rubric).

---

## 11. Implementation Phases

Each phase ends with a verifiable artifact. Numbers are agent-hours estimates for one engineer pair-coding with Claude.

| # | Phase | Deliverable | Verify | Est |
|---|---|---|---|---|
| 0 | Bootstrap | `pyproject.toml`, `uv.lock`, `.env.example`, FastAPI hello, docker-compose for local Neo4j, GCP auth | `make dev` boots; `/health` returns 200 | 1.5h |
| 1 | RAG foundation | `app/rag/` complete: parse → embed → index in Vertex AI VS; CitationQueryEngine wired | `scripts/seed_dora.py` indexes DORA PDF; querying returns chunks with page+char metadata | 4h |
| 2 | Schemas + Graph layer | `app/schemas/`, `app/graph/` complete; constraints/indexes applied at startup; idempotent upsert tested | `tests/integration/test_graph_upsert.py` passes against test container | 3h |
| 3 | Extraction agent | `app/agents/extraction.py`; ContractExtraction with citations; literal-substring validation of quotes | Run on fixture contract → valid Pydantic object with non-empty evidence | 5h |
| 4 | Graph builder + entity resolution | `app/agents/graph_builder.py` + `app/graph/resolver.py`; AWS / Amazon Web Services merges | Ingest 2 contracts mentioning same vendor differently → single `:Vendor` node | 4h |
| 5 | Risk scorer | `app/agents/risk_scorer.py`; criticality_score persists on nodes; `/api/graph` returns Sigma JSON with sized nodes | Demo contract set produces graph where AWS is largest node | 2h |
| 6 | Gap analysis agent | `app/agents/gap_analysis.py`; iterates 12 obligations; returns ObligationFinding with citations | Run end-to-end → at least 8/12 obligations have non-`weak_evidence` verdicts on hand-tuned fixture | 6h |
| 7 | Remediation agent | `app/agents/remediation.py` + `sovereign_alternatives.yaml`; proposes alternatives for `not_met` and high-concentration vendors | Critical vendor (AWS) → at least one EU sovereign alternative proposed with rationale | 3h |
| 8 | Report assembler | `app/agents/report_assembler.py`; `/api/report/{client_id}` returns Markdown + JSON | Renders human-readable audit doc with full citation appendix | 3h |
| 9 | Tracing (basic) | `app/tracing/`; structlog JSONL sink per session | After full demo run, `traces/{id}.jsonl` contains ordered step events | 2h |
| 10 | Demo polish | seed scripts, demo data, README, Makefile targets | `make demo` runs phases 1-8 against fixtures end-to-end with no manual steps | 2h |

**Total**: ~35h. Hackathon-feasible for 2 engineers across a weekend, single engineer across 4-5 focused days.

**Phases 1-2 are blockers for everything**. Phases 3, 4, 5 can parallelize once 1-2 land. Phases 6-8 depend on 3-5.

**Definition of Done per phase**: tests pass + manual end-to-end verification using `make` target + no `print()`-style debugging in committed code.

---

## 12. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Z.ai GLM-4.7 tool calling unstable on OpenAI-compatible endpoint** | Medium | High (extraction agent breaks) | Fallback to JSON-mode + Pydantic validation + retry; abstract behind `LLMClient` so we can swap to OpenAI / Anthropic in 5 min |
| **Vertex AI Vector Search v2.0 API surface changed since LlamaIndex integration** | Medium | High | Pin LlamaIndex VS package; verify with `scripts/seed_dora.py` early in Phase 1; fallback: in-memory `SimpleVectorStore` for demo, swap Vertex AI post-demo |
| **Entity resolution misses → fragmented graph → wrong concentration scores** | High | Medium | Test with 3 known aliases per major vendor; combine fuzzy + embedding similarity; manual canonicalization YAML as escape hatch (`vendor_aliases.yaml`) |
| **Citation hallucination (LLM cites span that doesn't exist)** | High | High | Literal substring validation post-LLM; reject + retry; if 2nd fails, downgrade to `weak_evidence` and surface flag in report |
| **DORA PDF parsing loses tables / structure** | Medium | Medium | Use LlamaParse premium (handles tables); pre-chunk fixture for tests so parser quality doesn't break test isolation |
| **Vertex AI quota / cold start latency** | Low | Medium | Pre-seed during demo setup; have `make seed-demo` run at venue arrival; fallback to local FAISS post-demo if quota explodes |
| **Demo fails live** | Always | Catastrophic | Pre-recorded video as backup; `make demo` regenerates everything from fixtures with one command; deterministic order of contract ingest |
| **Scope creep ("just add auth", "just add a UI")** | High | High | This document is the contract. New features → post-MVP doc, not this one |
| **Agents over-loop / bill** | Medium | Medium | Hard timeout per step (60s); max iteration budget per workflow (10 LLM calls); circuit-break on cost via env-var |
| **Graph viz lib choice locks us out** | Low | Low | We return generic Sigma-compatible JSON; swap to Reagraph / Cytoscape is cosmetic |

---

## 13. Pitch / Demo Script (3 minutes)

**Minute 1 — the problem**:
> "DORA goes live in EU finance. ICT third-party providers face fines of 1% of global daily revenue. Banks face GDPR-scale penalties. Today their compliance teams use spreadsheet tools that map controls but can't *read* a contract. We change that."

**Minute 2 — the demo (live)**:
1. Drop 3 vendor contracts (AWS, Stripe, internal SaaS) into `/api/ingest`.
2. Show the graph load — AWS is the biggest red node, 4 services connected, supports critical "Trading" function.
3. Click into AWS → "70% concentration risk; subcontractor chain depth 2 to a non-EU entity."
4. Show gap analysis report: 12 DORA obligations evaluated, `Art-30-3-e (Exit strategy)` is `not_met` — agent quotes the contract section that's silent on this AND quotes the DORA article requiring it.
5. Show remediation: "Migrate workloads to OVHcloud (sovereign EU). Estimated 18% cost increase. Feature delta: no Lambda equivalent, suggest Scaleway Serverless."

**Minute 3 — the wedge & ask**:
> "Vanta gives you a checkbox. Regulativ.ai gives you a dashboard. We give you an analyst that reads, reasons, and cites — at the speed of inference. On-premise deployable. Sovereign-aware. We're raising / hiring / piloting with [target bank]."

Close with one sentence on team / traction / ask.

---

## 14. Open Questions (for post-MVP)

These should *not* block MVP but need decisions before pilot:

1. **DORA obligation library**: who maintains the `dora_obligations.yaml`? (Internal compliance counsel? External legal partner?) Validation chain matters for sales credibility.
2. **Sovereign alternatives knowledge base**: ditto — who curates? Bias risk if we're paid to recommend.
3. **Multi-tenant isolation**: when on-prem, single-deployment-per-bank is fine. For SaaS pilot, need RBAC + per-tenant Neo4j databases or graph partitioning.
4. **LLM data residency**: Z.ai is hosted in China. For real EU bank deployment, must swap to EU-resident LLM (Mistral, Anthropic Frankfurt, Vertex Gemini in EU region). Build the swap now (we're already config-driven), but verify before any pilot conversation.
5. **Audit-trail signing**: regulators will eventually ask "how do we know this report wasn't tampered?" Hash the trace JSONL + sign with org key; cheap to add when we have a customer asking.
6. **Continuous monitoring**: contracts change. Re-ingest on update; diff findings; alert on regression.
7. **ERP / vendor management integration**: pull vendor list from ServiceNow / Coupa / SAP rather than manual upload.
8. **Frontend**: Next.js + Sigma.js + shadcn/ui; design language; report PDF rendering (LaTeX via Pandoc?).

---

## 15. Working Agreement

- **No mocked behavior in committed code.** A non-implemented branch returns 501 from the API and has a `#TODO(<owner>): <what + why>` comment with a link to the post-MVP issue. Never fabricate output.
- **Every agent claim cites.** Code path enforces this — citation list non-empty for any verdict ≠ `not_met`.
- **Karpathy guardrails apply**: no speculative abstractions, no error handling for impossible cases, surgical edits only. If a slice grows past 200 LOC, decompose or push back.
- **Latest dependencies, verified.** When implementing, run `uv pip install <pkg>@latest` and check the package CHANGELOG for breaking changes against the import surface in this plan.
- **The plan is the contract.** Scope changes update this file in the same PR, with rationale.
