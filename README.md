# DORA AI Analyst

> *The AI analyst for DORA, not another compliance dashboard.*

AI-powered DORA (Digital Operational Resilience Act) compliance analysis for EU financial institutions. Upload third-party vendor contracts → get explainable gap analysis with citations → visualise concentration risk as an interactive graph → receive sovereign EU remediation proposals.

## Quick start

```bash
# 1. Copy and fill in env vars
cp .env.example .env
# edit .env with your Z.ai, Gemini, GCP, and Neo4j credentials

# 2. Start local Neo4j
make neo4j-up

# 3. Install dependencies
uv sync

# 4. Start the API
make dev
# → http://localhost:8000
# → http://localhost:8000/docs  (OpenAPI)
# → http://localhost:8000/health
```

## Demo

```bash
# Pre-seed DORA regulation into vector store
make seed-dora

# Ingest fixture contracts + run full pipeline
make seed-demo
```

## Tech stack

| Layer | Tool |
|---|---|
| API | FastAPI 0.136+ |
| Agent orchestration | LlamaIndex Workflows 2.15+ |
| RAG + citations | LlamaIndex 0.14+ |
| LLM | Z.ai GLM-4.7 (OpenAI-compatible) |
| Embeddings | Gemini Embedding 2 (768-dim MRL) |
| Vector store | Vertex AI Vector Search v2.0 |
| Graph DB | Neo4j (AuraDB on GCP / local docker) |
| Document storage | GCS |
| Python | 3.13 |
| Package manager | uv |

## Architecture

See [PLAN.md](PLAN.md) for the full implementation plan, agent topology, graph schema, and domain model.

## Project structure

```
app/
  api/          HTTP routers (thin — orchestrate into agents/)
  agents/       LlamaIndex Workflows (extraction, graph, gap analysis, report)
  rag/          Vector store + CitationQueryEngine
  graph/        Neo4j client, schema, upsert, entity resolution
  schemas/      Pydantic models (ContractExtraction, ObligationFinding, ...)
  llm/          LLM + embedding client wrappers
  tracing/      Structured event logging per session
  data/         Static seed data (dora_obligations.yaml, sovereign_alternatives.yaml)
scripts/        One-shot seed + reset scripts
tests/          pytest unit + integration tests
```
