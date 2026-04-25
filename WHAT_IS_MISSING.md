# RegAgent -- What Is Missing for a Functional Prototype

This document tracks everything still needed to turn the current scaffold into a working demo.

Status: `[DONE]` shipped | `[PARTIAL]` scaffold exists, logic TODO | `[MISSING]` does not exist yet

---

## 1. GCP Infrastructure

| Item | Status | Details |
|------|--------|---------|
| Project `regagent-dora-2026` | `[DONE]` | Active, billing enabled |
| 11+ APIs enabled | `[DONE]` | Document AI, Vertex AI, Cloud Run, Artifact Registry, API Keys, etc. |
| GCS buckets | `[DONE]` | `regagent-documents-eu` + `regagent-reference-eu` |
| Artifact Registry | `[DONE]` | `regagent-repo` in europe-west9 |
| Document AI OCR processor | `[DONE]` | ID `9a4312989d6fb591`, EU region |
| Workload Identity Federation | `[DONE]` | Pool + provider + SA bindings |
| Vertex AI Gemini access | `[DONE]` | Gemini 2.5 Flash works via Vertex AI (`europe-west1`) and Generative Language API |
| Gemini API Key | `[DONE]` | `AIzaSyAMXHiamVrKqyk13nLBWkWKaLhbyR7vqPk` (restricted to `generativelanguage.googleapis.com`) |
| **Vertex AI Vector Search index** | `[MISSING]` | Must create index, endpoint, and deploy. Takes ~30 min. See `data_pipeline/vectorization/index_manager.py`. |
| **Upload reference data to GCS** | `[MISSING]` | Run `gsutil cp reference_data/*.json gs://regagent-reference-eu/` then vectorize. |
| **Secret Manager secrets** | `[MISSING]` | Consider storing API keys and processor IDs. |

---

## 2. Reference Data

### 2.1 What exists

| File | Status | Notes |
|------|--------|-------|
| `dora_article_30.json` | `[PARTIAL]` | 8 entries covering Art. 30(2)(a)-(g) and Art. 30(3). Missing full sub-paragraph text and Art. 28-29, 31. |
| `iso27001_controls.json` | `[PARTIAL]` | 7 controls (A.5.19-A.5.33). Missing A.8.x (encryption, logging, network). |
| `iso27005_methodology.json` | `[PARTIAL]` | Scoring methodology defined, no code implementation yet. |
| `roi_schema.json` | `[PARTIAL]` | 15 model IDs listed, no field-level validation. |
| `bank_rules_sample.json` | `[PARTIAL]` | 8 generic rules. Missing function-specific thresholds. |
| `bank_entity.json` | `[DONE]` | Full Eurobank profile with LEI, AUM, branches, group structure. |
| `bank_functions.json` | `[DONE]` | 6 critical functions with RTO/RPO targets. |
| `vendor_registry.json` | `[DONE]` | 5 ICT vendors with LEI, services, costs, certifications. |
| `vendor_contracts/*.json` | `[DONE]` | 5 simulated contract extracts (AWS, Bloomberg, SWIFT, Aladdin, CyberArk). |
| `concentration_matrix.json` | `[DONE]` | Cross-vendor dependencies and concentration risks. |

### 2.2 Still missing

| Data | Priority | Description |
|------|----------|-------------|
| `dora_articles_full.json` | HIGH | Expanded DORA coverage: Art. 5-9, 11, 15-16, 28-29. |
| `sample_pdfs/` | MEDIUM | PDF files for Document AI demo. Can use `docs/*.pdf` as test documents. |

---

## 3. Backend Implementation

### 3.1 Agents

| Agent | File | Status | What is missing |
|-------|------|--------|-----------------|
| Extractor | `extractor.py` | `[PARTIAL]` | Method stubs only. Implement: Document AI call, table parsing, clause splitting, embedding, Vector Search storage. |
| Evaluator | `evaluator.py` | `[PARTIAL]` | Method stubs only. Implement: semantic search, Gemini classification, ISO 27005 scoring, concentration analysis. |
| Orchestrator | `orchestrator.py` | `[PARTIAL]` | Method stubs only. Implement: gap analysis via Gemini, alert generation, RoI entry creation. |

### 3.2 Prompt Templates

| File | Status |
|------|--------|
| `prompts.py` | `[DONE]` | 6 prompt templates: system, extraction, classification, gap analysis, RoI generation, concentration risk. |

### 3.3 Services

| Service | Status | What is missing |
|---------|--------|-----------------|
| `document_ai.py` | `[PARTIAL]` | Basic `process_document` works. Missing: batch processing, table extraction. |
| `vertex_ai.py` | `[PARTIAL]` | Basic methods. Missing: structured JSON output, system instructions, temperature settings. |
| `vector_search.py` | `[PARTIAL]` | Stub only. Must implement Vector Search SDK calls. |
| `storage.py` | `[PARTIAL]` | Basic upload/download. Missing: list objects, signed URLs. |

### 3.4 Routers

| Router | Status | What is missing |
|--------|--------|-----------------|
| `documents.py` | `[PARTIAL]` | Wire up: storage upload, extractor call, status return. |
| `analysis.py` | `[PARTIAL]` | Wire up: evaluator + orchestrator, result storage. |
| `alerts.py` | `[PARTIAL]` | Implement: alert storage, severity filtering, CRO validation. |
| `register.py` | `[PARTIAL]` | Implement: RoI aggregation, CSV export. |

### 3.5 Data Persistence

`[MISSING]` -- Options:
- **Simplest**: In-memory Python dicts (reset on restart, fine for demo)
- **Better**: JSON files on Cloud Storage
- **Best**: Firestore

---

## 4. Frontend

### 4.1 Build Configuration

| File | Status |
|------|--------|
| `tsconfig.json` | `[DONE]` |
| `vite.config.ts` | `[DONE]` |
| `index.html` | `[DONE]` |
| `src/main.tsx` | `[DONE]` |

### 4.2 UI Components

All 5 components exist with placeholder content. Need real implementation:

| Component | Must implement |
|-----------|---------------|
| `Dashboard.tsx` | KPI cards, recent alerts list, risk gauge. API: `GET /api/alerts`, `GET /api/register`. |
| `ContractUpload.tsx` | Drag-and-drop PDF upload, progress bar. API: `POST /api/documents/upload`. |
| `GapAnalysis.tsx` | Per-vendor gap table with severity coloring. API: `GET /api/analysis/results/{id}`. |
| `RiskMap.tsx` | Vendor dependency graph or table with concentration scores. |
| `RegisterView.tsx` | Tabular RoI view with CSV export button. |

### 4.3 Styling

`[MISSING]` -- No CSS framework. Recommended: Tailwind CSS + shadcn/ui or Chakra UI.

---

## 5. Data Pipeline

| File | Status | What is missing |
|------|--------|-----------------|
| `extract_text.py` | `[PARTIAL]` | Implement Document AI batch API call. |
| `chunker.py` | `[PARTIAL]` | Implement clause-aware chunking (regex: `Article \d+`, `Section \d+`). |
| `embed.py` | `[PARTIAL]` | Implement `TextEmbeddingModel.get_embeddings()` with batching. |
| `index_manager.py` | `[PARTIAL]` | Implement index creation (768 dims, DOT_PRODUCT). |
| `load_reference.py` | `[PARTIAL]` | Load JSONs, convert to text chunks, embed, upsert to Vector Search. |

---

## 6. CI/CD & DevOps

| Item | Status |
|------|--------|
| `deploy-backend.yml` | `[DONE]` |
| `deploy-frontend.yml` | `[DONE]` |
| `.env.example` | `[DONE]` |
| **Docker Compose** | `[MISSING]` -- Useful for local development. |
| **`package-lock.json`** | `[MISSING]` -- Run `npm install` in `frontend/`. |

---

## 7. Testing & Demo

| Item | Status |
|------|--------|
| Unit tests | `[MISSING]` -- At minimum: test scoring, DORA mapping, Pydantic schemas. |
| Sample PDF | `[MISSING]` -- Use `docs/navigating-gdpr-compliance.pdf` as test input. |
| Pre-computed demo | `[MISSING]` -- Pre-compute one full analysis for reliable live demo. |

---

## 8. Priority Execution Order

### Immediate (Foundation)
1. `npm install` in frontend
2. Install Tailwind/Chakra UI

### Hour 1-4 (Core Logic)
3. Implement `vertex_ai.py` with Gemini 2.5 Flash structured JSON
4. Implement `evaluator.py` using prompts + reference data
5. Implement `orchestrator.py` gap analysis logic
6. Implement basic in-memory persistence

### Hour 4-8 (Pipeline)
7. Implement `extractor.py` with Document AI
8. Create Vector Search index + deploy
9. Run `load_reference.py` to populate index
10. Implement `vector_search.py`

### Hour 8-14 (Frontend)
11. Install CSS framework
12. Build Dashboard with real API calls
13. Build ContractUpload with drag-and-drop
14. Build GapAnalysis with severity table
15. Build RegisterView with export

### Hour 14-20 (Integration)
16. Wire up all routers to agents
17. Pre-compute demo flow
18. Test full pipeline end-to-end
19. Deploy to Cloud Run

### Hour 20-24 (Polish)
20. UI polish and responsive design
21. Prepare 3-minute pitch
22. Final deployment
