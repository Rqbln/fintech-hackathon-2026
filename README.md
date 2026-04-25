# RegAgent -- Automated DORA Compliance Platform

**Paris Fintech Hackathon 2026** | HEC Paris | April 25-26, 2026

RegAgent is a multi-agent Compliance Tech platform that automates Third-Party Risk Management (TPRM) under the EU Digital Operational Resilience Act (DORA). It transforms unstructured vendor documents (contracts, SLAs, SOC 2 reports) into actionable compliance alerts for Chief Risk Officers.

## Architecture

Three specialized AI agents work in sequence:

1. **Extractor Agent** -- Ingests vendor PDFs via Google Document AI, extracts security guarantees and SLA tables
2. **Evaluator Agent** -- Maps extracted clauses to ISO 27001/27005 controls and DORA Article 30 requirements, computes concentration risk scores
3. **Orchestrator Agent** -- Performs Gap Analysis (bank internal rules vs. contractual guarantees), generates critical alerts with Human-in-the-loop validation

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | Gemini 1.5 Pro/Flash via Vertex AI |
| OCR | Google Cloud Document AI |
| Vector DB | Vertex AI Vector Search |
| Embeddings | Vertex AI Text Embeddings (`text-multilingual-embedding`) |
| Backend | FastAPI on Cloud Run |
| Frontend | React on Cloud Run |
| CI/CD | GitHub Actions + Workload Identity Federation |
| Region | `europe-west9` (Paris) |

## Project Structure

```
backend/          FastAPI backend with multi-agent architecture
frontend/         React dashboard for CRO alerts
data_pipeline/    Document ingestion and vectorization scripts
reference_data/   DORA/ISO reference framework (JSON)
infra/            Infrastructure as Code (Terraform)
docs/             Strategic analysis documents
```

## GCP Project

- **Project ID**: `regagent-dora-2026`
- **Billing**: Trial account `010D06-E96374-20CEED`
- **Document AI Processor**: `9a4312989d6fb591` (OCR, EU region)

## Getting Started

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Team

5 engineers -- ML, Cybersecurity, Web Architecture
