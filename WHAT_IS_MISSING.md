# RegAgent -- What Is Missing for a Functional Prototype

This document is the single source of truth for everything that still needs to be built, enriched, or connected to turn the current scaffold into a working demo for the Paris Fintech Hackathon 2026 (24h sprint).

Status legend: `[DONE]` shipped, `[PARTIAL]` scaffold exists but logic is TODO, `[MISSING]` does not exist yet.

---

## 1. GCP Infrastructure

| Item | Status | Details |
|------|--------|---------|
| Project `regagent-dora-2026` | `[DONE]` | Active, billing enabled |
| 11 APIs enabled | `[DONE]` | Document AI, Vertex AI, Cloud Run, etc. |
| GCS buckets | `[DONE]` | `regagent-documents-eu` + `regagent-reference-eu` |
| Artifact Registry | `[DONE]` | `regagent-repo` in europe-west9 |
| Document AI OCR processor | `[DONE]` | ID `9a4312989d6fb591`, EU region |
| Workload Identity Federation | `[DONE]` | Pool + provider + SA bindings |
| **Vertex AI GenAI terms acceptance** | `[MISSING]` | Must manually accept at https://console.cloud.google.com/vertex-ai?project=regagent-dora-2026 -- navigate to Model Garden > Gemini and click Enable. Without this, all Gemini API calls return 404. |
| **Vertex AI Vector Search index** | `[MISSING]` | No index has been created yet. Must create an index, create an endpoint, and deploy the index to the endpoint. This takes ~30 min. See `data_pipeline/vectorization/index_manager.py`. |
| **Upload reference data to GCS** | `[MISSING]` | The files in `reference_data/` must be uploaded to `gs://regagent-reference-eu/` and then vectorized into the Vector Search index. |
| **Secret Manager secrets** | `[MISSING]` | No secrets stored yet. Consider storing `DOCAI_PROCESSOR_ID` and any API keys there. |

---

## 2. Reference Data (the "brain" of the system)

### 2.1 What exists (scaffold-level)

| File | Status | Gap |
|------|--------|-----|
| `dora_article_30.json` | `[PARTIAL]` | Only 8 entries covering Art. 30(2)(a)-(g) and Art. 30(3). Missing the full text of sub-paragraphs, the complete Art. 28-29 (general TPRM framework), and Art. 31 (concentration risk criteria). |
| `iso27001_controls.json` | `[PARTIAL]` | Only 7 controls (A.5.19-A.5.33). Missing A.8.x (technology controls: encryption, logging, network security) which are frequently referenced in vendor contracts. |
| `iso27005_methodology.json` | `[PARTIAL]` | Scoring methodology defined but no actual scoring implementation in code. |
| `roi_schema.json` | `[PARTIAL]` | Lists 15 model IDs and field names but no field-level validation rules, data types, or enum values needed for actual RoI generation. |
| `bank_rules_sample.json` | `[PARTIAL]` | Only 8 generic rules. Missing function-specific thresholds, vendor-specific overrides, and the link to the bank entity profile. |

### 2.2 What is completely missing

| Data | Priority | Description |
|------|----------|-------------|
| **`reference_data/bank_entity.json`** | CRITICAL | The fictitious bank's identity: name, LEI code, country, branches, group structure, competent authority, total AUM, number of employees. This is model B_01.01-B_01.03 in the RoI. |
| **`reference_data/bank_functions.json`** | CRITICAL | Inventory of the bank's critical and important business functions (payment processing, portfolio management, custody, trade execution, risk reporting, client onboarding). Each with criticality, RTO/RPO targets, and licensing authority. This is model B_05.01. |
| **`reference_data/vendor_registry.json`** | CRITICAL | The bank's ICT third-party service providers. At least 5-8 realistic vendors (cloud, market data, trading platform, cybersecurity, payments, messaging). Each with LEI, country, services provided, contract dates, annual cost, certifications. This is models B_03.01-B_03.03. |
| **`reference_data/vendor_contracts/`** | CRITICAL | Simulated contract extracts (JSON) for each vendor in the registry. Each should contain: SLA clauses, data residency info, audit rights, subcontracting chains, exit provisions. This is the data the Extractor Agent would produce after parsing a real PDF. |
| **`reference_data/dora_articles_full.json`** | HIGH | Expanded DORA coverage beyond Art. 30. Should include Art. 5-9 (ICT risk management framework), Art. 11 (response and recovery), Art. 15-16 (digital resilience testing), Art. 28 (general TPRM principles), Art. 29 (preliminary assessment). |
| **`reference_data/concentration_matrix.json`** | HIGH | Cross-vendor dependency matrix showing shared infrastructure (e.g., vendor A and vendor B both depend on AWS eu-west-1). Essential for the concentration risk scoring. |
| **`reference_data/sample_pdfs/`** | MEDIUM | Actual PDF files to demo the Document AI extraction pipeline. Could use the existing `docs/navigating-gdpr-compliance.pdf` or create mock vendor contracts as PDFs. |

---

## 3. Backend Implementation

### 3.1 Agents (the core logic)

| Agent | File | Status | What is missing |
|-------|------|--------|-----------------|
| **Extractor** | `backend/app/agents/extractor.py` | `[PARTIAL]` | Method stubs only. Must implement: (1) Call Document AI `process_document`, (2) Parse the returned `Document` object to extract tables, key-value pairs, and clause text, (3) Use LangChain `RecursiveCharacterTextSplitter` or custom clause-aware splitter, (4) Call Vertex AI Embeddings to vectorize chunks, (5) Store vectors in Vector Search. |
| **Evaluator** | `backend/app/agents/evaluator.py` | `[PARTIAL]` | Method stubs only. Must implement: (1) Load DORA/ISO reference from Vector Search, (2) For each extracted clause, semantic search for matching requirements, (3) Send clause + requirement to Gemini with a structured prompt asking for compliance classification, (4) Aggregate scores using ISO 27005 methodology weights. |
| **Orchestrator** | `backend/app/agents/orchestrator.py` | `[PARTIAL]` | Method stubs only. Must implement: (1) Load bank internal rules from `bank_rules_sample.json` (or Vector Search), (2) Compare each vendor guarantee against bank thresholds, (3) Send structured prompt to Gemini asking for gap identification, (4) Generate severity-ranked `Alert` objects, (5) Produce `RegisterEntry` for the RoI. |

### 3.2 Prompt Templates

`[MISSING]` -- No prompt templates exist anywhere. These are critical for Gemini to produce structured, reliable output.

Need to create **`backend/app/agents/prompts.py`** containing:

1. **EXTRACTION_PROMPT** -- Given OCR text, extract structured clause data (category, SLA values, entities).
2. **CLASSIFICATION_PROMPT** -- Given a clause and a DORA/ISO requirement, classify compliance as `compliant`, `partial`, or `non_compliant` with evidence.
3. **GAP_ANALYSIS_PROMPT** -- Given bank internal rule + vendor guarantee, identify gaps and rate severity.
4. **ROI_GENERATION_PROMPT** -- Given vendor data, generate a Register of Information entry following the RoI schema.

### 3.3 Services

| Service | File | Status | What is missing |
|---------|------|--------|-----------------|
| `document_ai.py` | `[PARTIAL]` | Basic `process_document` works. Missing: batch processing, table extraction parsing, page-level iteration. |
| `vertex_ai.py` | `[PARTIAL]` | Basic `generate` and `embed_texts` work. Missing: system instructions, structured JSON output mode, temperature/safety settings. |
| `vector_search.py` | `[PARTIAL]` | Stub only. Must implement actual Vertex AI Vector Search SDK calls (`MatchingEngineIndex`, `MatchingEngineIndexEndpoint`). |
| `storage.py` | `[PARTIAL]` | Basic upload/download. Missing: list objects, signed URL generation for frontend PDF preview. |

### 3.4 Routers (API endpoints)

| Router | Status | What is missing |
|--------|--------|-----------------|
| `documents.py` | `[PARTIAL]` | Must wire up: read uploaded bytes, call `storage.upload_document`, call `extractor.extract`, return extraction status. |
| `analysis.py` | `[PARTIAL]` | Must wire up: call `evaluator.evaluate`, then `orchestrator.gap_analysis`, store results, return analysis. |
| `alerts.py` | `[PARTIAL]` | Must implement: in-memory or persistent alert storage, filtering by severity, CRO validation workflow. |
| `register.py` | `[PARTIAL]` | Must implement: aggregate all vendor data into RoI models, export in CSV format. |

### 3.5 Data Persistence

`[MISSING]` -- No persistence layer exists. Options for the hackathon:

- **Simplest**: In-memory Python dicts/lists (reset on restart, fine for a 24h demo).
- **Better**: JSON files on Cloud Storage.
- **Best**: Firestore or Cloud SQL (adds complexity but impresses jury).

---

## 4. Frontend

### 4.1 Build Configuration

`[MISSING]` -- The React app cannot build. Missing essential files:

| File | Description |
|------|-------------|
| `frontend/tsconfig.json` | TypeScript configuration |
| `frontend/tsconfig.app.json` | App-specific TS config |
| `frontend/tsconfig.node.json` | Node-specific TS config |
| `frontend/vite.config.ts` | Vite bundler configuration (with React plugin) |
| `frontend/index.html` | HTML entry point with `<div id="root">` |
| `frontend/src/main.tsx` | React entry point rendering `<App />` |
| `frontend/src/vite-env.d.ts` | Vite type declarations |

### 4.2 UI Components

All 5 components exist but contain only placeholder `<div>` elements. They need:

| Component | Must implement |
|-----------|---------------|
| `Dashboard.tsx` | Summary cards (total vendors, compliance rate, critical alerts count), recent alerts list, overall risk gauge. API calls to `GET /api/alerts` and `GET /api/register`. |
| `ContractUpload.tsx` | Drag-and-drop PDF upload, progress bar, file validation. API call to `POST /api/documents/upload`. |
| `GapAnalysis.tsx` | Per-vendor gap table with columns: DORA Article, Bank Requirement, Vendor Guarantee, Gap, Severity. Color-coded by severity. API call to `GET /api/analysis/results/{id}`. |
| `RiskMap.tsx` | Vendor dependency graph (could use a simple table or a D3/recharts visualization). Shows concentration scores and shared infrastructure. |
| `RegisterView.tsx` | Tabular view of all RoI entries with export button (CSV download). |

### 4.3 Styling & UI Library

`[MISSING]` -- No CSS framework installed. Recommended for speed:

- **Tailwind CSS** + **shadcn/ui** (best quality, moderate setup time)
- **Chakra UI** (fast, good defaults)
- **Plain CSS modules** (zero dependency, fastest to start)

---

## 5. Data Pipeline

### 5.1 Ingestion pipeline

| File | Status | What is missing |
|------|--------|-----------------|
| `extract_text.py` | `[PARTIAL]` | Stub. Must implement GCS-triggered extraction using Document AI batch API. |
| `chunker.py` | `[PARTIAL]` | Stub. Must implement clause-aware chunking. Legal documents need splitting on article/section boundaries, not arbitrary character counts. Recommended: regex-based splitting on patterns like `Article \d+`, `Section \d+`, `\d+\.\d+`. |

### 5.2 Vectorization pipeline

| File | Status | What is missing |
|------|--------|-----------------|
| `embed.py` | `[PARTIAL]` | Stub. Must call `TextEmbeddingModel.get_embeddings()` with batching (max 250 texts per call). |
| `index_manager.py` | `[PARTIAL]` | Stub. Must implement index creation with correct dimensions (768 for `text-multilingual-embedding-002`), distance measure (DOT_PRODUCT_DISTANCE or COSINE), and deployment to endpoint. |

### 5.3 Reference data loading

| File | Status | What is missing |
|------|--------|-----------------|
| `load_reference.py` | `[PARTIAL]` | Reads JSON files but does not vectorize or upload them. Must: (1) Load all reference JSONs, (2) Convert each entry to a text chunk, (3) Embed via Vertex AI, (4) Upsert into Vector Search index with metadata (source, article_id, category). |

---

## 6. CI/CD & DevOps

| Item | Status | Details |
|------|--------|---------|
| `deploy-backend.yml` | `[DONE]` | Workflow complete with WIF auth |
| `deploy-frontend.yml` | `[DONE]` | Workflow complete with WIF auth |
| **`.env.example`** | `[MISSING]` | No environment variable documentation. Developers won't know what to configure. |
| **Docker Compose (local dev)** | `[MISSING]` | No way to run backend + frontend locally together. A `docker-compose.yml` would help during development. |
| **Frontend `package-lock.json`** | `[MISSING]` | Must run `npm install` in `frontend/` to generate lockfile before Docker build works. |

---

## 7. Testing & Demo Data

| Item | Status | Details |
|------|--------|---------|
| **Unit tests** | `[MISSING]` | No tests exist. At minimum: test the scoring algorithm, test the DORA mapping logic, test the Pydantic schemas. |
| **Sample PDF for demo** | `[MISSING]` | Need at least 1 realistic vendor contract PDF to demonstrate the full pipeline during the live demo. The `docs/navigating-gdpr-compliance.pdf` can serve as a first test document. |
| **Pre-computed demo results** | `[MISSING]` | For a reliable hackathon demo, pre-compute at least one full analysis (extraction -> evaluation -> gap analysis -> alerts) and store the results so the frontend can display them even if the pipeline fails live. |

---

## 8. Priority Execution Order (24h Hackathon)

For maximum demo impact, build in this order:

### Hour 0-2: Foundation
1. Accept Vertex AI terms in GCP Console
2. Complete frontend build config (tsconfig, vite, index.html, main.tsx)
3. Create `.env.example`
4. `npm install` in frontend

### Hour 2-6: Data Layer
5. Create `bank_entity.json` (fictitious bank profile)
6. Create `bank_functions.json` (critical function inventory)
7. Create `vendor_registry.json` (5-8 realistic vendors)
8. Create `vendor_contracts/*.json` (simulated contract extracts for each vendor)
9. Create `concentration_matrix.json`

### Hour 6-10: Agent Prompts + Gemini Integration
10. Write `backend/app/agents/prompts.py` (all 4 prompt templates)
11. Implement `vertex_ai.py` with structured JSON output
12. Implement `evaluator.py` using prompts + reference data
13. Implement `orchestrator.py` gap analysis logic

### Hour 10-14: Pipeline
14. Implement `extractor.py` with Document AI integration
15. Implement `vector_search.py` with Vertex AI SDK
16. Create Vector Search index + deploy
17. Run `load_reference.py` to populate index

### Hour 14-20: Frontend
18. Install Tailwind or Chakra UI
19. Build `Dashboard.tsx` with real API calls
20. Build `ContractUpload.tsx` with drag-and-drop
21. Build `GapAnalysis.tsx` with severity table
22. Build `RegisterView.tsx` with export

### Hour 20-24: Polish & Demo Prep
23. Pre-compute one full demo flow
24. Test full pipeline end-to-end
25. Deploy to Cloud Run
26. Prepare 3-minute pitch

---

## 9. Files to Create (Complete List)

```
NEW FILES NEEDED:
  reference_data/
    bank_entity.json                    # Fictitious bank identity (B_01.01)
    bank_functions.json                 # Critical function inventory (B_05.01)
    vendor_registry.json                # ICT vendor registry (B_03.01)
    vendor_contracts/
      aws_cloud_contract.json           # Simulated AWS contract extract
      bloomberg_data_contract.json      # Simulated Bloomberg contract
      swift_messaging_contract.json     # Simulated SWIFT contract
      aladdin_platform_contract.json    # Simulated Aladdin contract
      cyberark_security_contract.json   # Simulated CyberArk contract
    concentration_matrix.json           # Cross-vendor dependency matrix
    dora_articles_full.json             # Expanded DORA coverage (Art. 5-31)

  backend/app/agents/
    prompts.py                          # Gemini prompt templates

  frontend/
    tsconfig.json
    tsconfig.app.json
    tsconfig.node.json
    vite.config.ts
    index.html
    src/main.tsx
    src/vite-env.d.ts

  .env.example                          # Environment variable template
```
