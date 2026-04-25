# What Was Built This Session

## Phase 2 — Pydantic Schemas + Neo4j Graph Layer

### `app/schemas/`
Single source of truth for all inter-layer data contracts.

| File | Exports |
|---|---|
| `contract.py` | `EvidenceSpan`, `ServiceClause`, `ContractExtraction` |
| `obligation.py` | `Verdict` (enum: met/partially_met/unmet/unknown), `ObligationFinding` |
| `graph.py` | `GraphNode`, `GraphEdge`, `GraphResponse` — Sigma.js-compatible shapes |
| `remediation.py` | `AlternativeVendor`, `RemediationProposal` |
| `report.py` | `ReportArtifact` |

### `app/graph/`
Async Neo4j layer with no business logic — pure data access.

| File | Purpose |
|---|---|
| `client.py` | `run_read` / `run_write` — thin async session wrappers |
| `schema.py` | 5 Cypher constraints + 2 indexes, applied at startup via `apply_schema()` |
| `upsert.py` | Idempotent `MERGE` statements for Vendor, Service, Contract, DORAObligation, EVIDENCES edge, DEPENDS_ON edge |
| `queries.py` | `get_graph()` (full or subgraph, Sigma-ready) + `get_vendor_concentration()` |
| `resolver.py` | Entity resolution: exact match → fuzzy (rapidfuzz token_sort_ratio ≥ 90) → new slug |

### `app/api/graph.py`
- `GET /api/graph` — Sigma.js-compatible JSON (optional `root_vendor` + `depth` params)
- `GET /api/graph/concentration` — vendors ranked by `criticality_score`

---

## Phase 3 — ExtractionAgent

### `app/agents/extraction.py`
- JSON-mode LLM prompting (no function-calling — Cerebras compatibility)
- Extracts: vendor name/country, services + SLAs, DORA obligation ids, evidence spans, sub-vendors
- Auto-strips markdown fences from LLM output
- One retry with correction prompt on JSON parse failure
- Truncates contracts to 12 000 chars to stay within token budget

### `app/agents/events.py`
LlamaIndex Workflow event types: `DocParsedEvent`, `ExtractedEvent`, `GraphUpdatedEvent`, `IngestionResult`

---

## Phase 4 — GraphBuilderAgent

### `app/agents/graph_builder.py`
- Loads all known `Vendor` nodes from Neo4j before each ingest
- Runs entity resolution (`resolver.py`) to deduplicate vendor names
- Calls `upsert_extraction()` — writes Vendor, Services, Contract, sub-vendor DEPENDS_ON edges

---

## Phase 5 — RiskScorer

### `app/agents/risk_scorer.py`
Recomputes `criticality_score ∈ [0, 1]` for every Vendor after each ingest:

```
score = contracts × 0.3   (cap: 5)
      + services  × 0.3   (cap: 10)
      + dependents× 0.2   (cap: 3)
      + country_risk × 0.2
```

`country_risk`: 0.0 for EU/EEA, 0.5 for unknown, 1.0 for non-EU.
Score drives node size in the Sigma.js graph.

---

## ContractIngestionWorkflow

### `app/agents/ingestion.py`
LlamaIndex `Workflow` with 4 chained `@step` handlers:

```
StartEvent(file_bytes, contract_id)
  → parse_and_index   → DocParsedEvent      # PDF → Vertex AI VS
  → extract           → ExtractedEvent      # ExtractionAgent
  → build_graph_step  → GraphUpdatedEvent   # GraphBuilderAgent
  → score_risks       → StopEvent           # RiskScorer
```

`POST /api/ingest` now runs the full workflow and returns `vendor_name`, `vendor_id`, `criticality_score`.

---

## Phase 6 — GapAnalysisAgent

### `app/agents/gap_analysis.py`
For each of the 12 DORA Art.30 obligations (`app/data/dora_obligations.yaml`):
1. Queries `CitationQueryEngine` with the obligation text
2. Sends RAG context + contract preview to LLM
3. Parses structured verdict: `met / partially_met / unmet / unknown`
4. Returns `ObligationFinding` with rationale, gap description, risk level, evidence spans

---

## Phase 7 — RemediationAgent

### `app/agents/remediation.py`
For each `unmet` / `partially_met` finding:
1. Fuzzy-matches the vendor name against `app/data/sovereign_alternatives.yaml`
2. Builds `AlternativeVendor` list (OVHcloud, Scaleway, Outscale, etc.)
3. Asks LLM for a remediation plan with priority, detail, effort estimate, DORA references
4. Returns `RemediationProposal` per finding

---

## Phase 8 — ReportAssembler + Report API

### `app/agents/report_assembler.py`
- Aggregates all findings + proposals
- Computes `obligations_met / partial / unmet` counts
- Derives `overall_risk_level` (low / medium / high / critical)
- Asks LLM for a board-level executive summary (≤ 200 words)
- Returns `ReportArtifact`

### `app/api/analysis.py`
`POST /api/gap-analysis` — full pipeline in one call:
- Input: `contract_ids`, `vendor_name`, `contract_text_preview`, optional `obligation_ids`
- Output: `ReportArtifact` (JSON)

### `app/api/report.py`
- `GET /api/report/{session_id}` — JSON report
- `GET /api/report/{session_id}/markdown` — Markdown export with findings table, gap descriptions, evidence quotes, EU-sovereign alternatives

---

## Phase 9 — Demo Fixture + Integration Script

### `tests/fixtures/demo_aws_contract.txt`
Realistic fictitious AWS EMEA contract covering: scope of services, subcontracting, data residency, encryption, SLAs, audit rights, incident reporting, termination/exit.

### `scripts/test_pipeline.py`
6-step integration script runnable without a live HTTP server:
1. ExtractionAgent
2. GraphBuilder
3. RiskScorer
4. GapAnalysisAgent (2 obligations for speed)
5. RemediationAgent
6. ReportAssembler

```bash
make pipeline
```

---

## Tests

| File | Tests | Covers |
|---|---|---|
| `test_schemas.py` | 7 | All Pydantic schema shapes |
| `test_resolver.py` | 5 | Entity resolution exact + fuzzy + slug generation |
| `test_extraction.py` | 8 | JSON parsing, markdown fence stripping, Pydantic building, truncation |
| `test_risk_scorer.py` | 5 | Country risk function, EU-27 + EEA membership |
| `test_gap_analysis.py` | 5 | Obligations YAML loading, verdict JSON parsing |
| `test_remediation.py` | 6 | Vendor fuzzy matching, alternative building |
| `test_report.py` | 5 | Markdown rendering, in-memory store |
| `test_obligations_yaml.py` | 4 | YAML integrity |
| `test_sovereign_yaml.py` | 4 | YAML integrity |
| **Total** | **49** | **49/49 pass** |

---

## API Surface (complete)

| Method | Path | Status | Description |
|---|---|---|---|
| `GET` | `/health` | live | Neo4j + key checks |
| `POST` | `/api/ingest/dora` | live | Seed DORA regulation (idempotent) |
| `POST` | `/api/ingest` | live | Upload contract → full AI pipeline |
| `GET` | `/api/graph` | live | Sigma.js graph JSON |
| `GET` | `/api/graph/concentration` | live | Vendor criticality ranking |
| `POST` | `/api/gap-analysis` | live | DORA gap analysis → ReportArtifact |
| `GET` | `/api/report/{id}` | live | JSON report |
| `GET` | `/api/report/{id}/markdown` | live | Markdown report |
| `GET` | `/api/sessions/{id}/trace` | TODO | Agent trace (post-MVP) |
| `GET` | `/api/remediation` | TODO | Phase TBD |

---

## Commits This Session

| Hash | Message |
|---|---|
| `cc3d972` | feat: Phase 2 — Pydantic schemas + Neo4j graph layer |
| `3362abb` | feat: Phase 3-5 — ExtractionAgent, GraphBuilder, RiskScorer + ContractIngestionWorkflow |
| `c95ecee` | feat: Phase 6-8 — GapAnalysisAgent, RemediationAgent, ReportAssembler |
| `9297012` | feat: Phase 9 — demo fixture + pipeline integration script + Makefile targets |
