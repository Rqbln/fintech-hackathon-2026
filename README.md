# RegAgent -- Automated DORA Compliance Platform

**Paris Fintech Hackathon 2026** | HEC Paris | April 25-26, 2026

RegAgent is a multi-agent AI platform that automates Third-Party Risk Management (TPRM) under the EU Digital Operational Resilience Act (DORA). It transforms unstructured vendor documents (contracts, SLAs, SOC 2 reports) into actionable compliance alerts for Chief Risk Officers.

## How It Works

```
PDF Upload → OCR (Document AI) → Extractor Agent → Structured Clauses
                                                          ↓
DORA/ISO Reference (Vector Search) ← Evaluator Agent → Compliance Scores
                                                          ↓
Bank Internal Rules ← Orchestrator Agent → Alerts + Register of Information
                                                    ↓
                                            CRO Dashboard (React)
```

Three specialized AI agents powered by **Gemini 2.5 Flash**:

1. **Extractor** -- Ingests vendor PDFs via Document AI, extracts SLA clauses and security guarantees
2. **Evaluator** -- Maps clauses to DORA Article 30 / ISO 27001 controls, computes risk scores
3. **Orchestrator** -- Compares guarantees against bank rules, generates critical alerts

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | Gemini 2.5 Flash (Vertex AI) |
| OCR | Google Cloud Document AI |
| Vector DB | Vertex AI Vector Search |
| Embeddings | Vertex AI Text Embeddings (`text-multilingual-embedding-002`) |
| Backend | FastAPI (Python 3.12) on Cloud Run |
| Frontend | React + TypeScript + Vite on Cloud Run |
| CI/CD | GitHub Actions + Workload Identity Federation |

## Quick Start

```bash
# Backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080

# Frontend
cd frontend && npm install && npm run dev
```

## Documentation

| Document | Description |
|----------|-------------|
| [docs/PROJECT.md](docs/PROJECT.md) | Documentation complète du projet |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture technique détaillée |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Guide de démarrage développeur |
| [WHAT_IS_MISSING.md](WHAT_IS_MISSING.md) | Tâches restantes pour le prototype |

## Project Structure

```
backend/          FastAPI backend with multi-agent architecture
frontend/         React CRO dashboard
data_pipeline/    Document ingestion & vectorization scripts
reference_data/   DORA/ISO reference + fictitious bank data (JSON)
docs/             Project documentation
  ├── research/   Strategic research documents (pre-hackathon)
  ├── PROJECT.md  Full project overview
  └── ARCHITECTURE.md  Technical architecture
```

## GCP Project

- **Project**: `regagent-dora-2026`
- **Region**: `europe-west1` / `europe-west9`
- **Billing**: Trial account with $300 credits
- **APIs**: Document AI, Vertex AI, Cloud Run, Artifact Registry, Cloud Storage, Secret Manager

## Team

5 engineers -- ML, Cybersecurity, Web Architecture
