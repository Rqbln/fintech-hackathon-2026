# Pipeline d'ingestion — RegAgent

## Ce que fait la pipeline

Prend un contrat vendeur PDF → extrait le texte + tables → découpe en clauses DORA → indexe dans le RAG Vertex AI.

```
PDF (GCS)
  └─▶ Document AI OCR        app/services/document_ai.py
        └─▶ Chunker LangChain  app/utils/chunker.py
              └─▶ RAG Corpus    app/services/rag_engine.py
                    └─▶ Gemini  app/services/vertex_ai.py
```

---

## Structure des fichiers

```
backend/
├── app/
│   ├── config.py                  Variables d'env GCP (projet, région, buckets...)
│   ├── main.py                    FastAPI — routes montées ici
│   │
│   ├── agents/
│   │   ├── extractor.py           Orchestrateur : appelle Document AI → chunker → RAG
│   │   ├── evaluator.py           TODO : scoring DORA par clause (Gemini)
│   │   ├── orchestrator.py        TODO : gap analysis + génération alertes CRO
│   │   └── prompts.py             Templates prompts Gemini pour les 3 agents
│   │
│   ├── models/
│   │   ├── schemas.py             Modèles Pydantic (VendorDocument, ExtractedClause, Alert...)
│   │   └── dora_mapping.py        Mapping DORA Art.30 → contrôles ISO 27001
│   │
│   ├── routers/
│   │   ├── documents.py           POST /api/documents/upload — pipeline complète ✅
│   │   ├── analysis.py            TODO : POST /api/analysis/gap
│   │   ├── alerts.py              TODO : GET /api/alerts
│   │   └── register.py            TODO : GET /api/register (RoI DORA)
│   │
│   ├── services/
│   │   ├── document_ai.py         OCR via Google Document AI (split auto si > 15 pages)
│   │   ├── rag_engine.py          Corpus RAG Vertex AI (create/upload/query)
│   │   ├── storage.py             Upload/download GCS
│   │   └── vertex_ai.py           Appels Gemini (generate + embeddings)
│   │
│   └── utils/
│       └── chunker.py             Split texte juridique + catégorisation DORA
│
├── requirements.txt
├── Dockerfile
└── PIPELINE.md                    ← ce fichier

data_pipeline/
└── reference/
    └── load_reference.py          Script one-shot : charge DORA/ISO/règles banque dans le RAG
```

---

## Services GCP utilisés

| Service | Ressource | Région |
|---|---|---|
| Document AI | Processor `9a4312989d6fb591` (OCR) | `eu` |
| Cloud Storage | `regagent-documents-eu` | `europe-west9` |
| Vertex AI RAG | Corpus `regagent-corpus-v1` | `europe-west1` |
| Vertex AI Gemini | `gemini-2.5-flash` | `europe-west9` |

> RAG Engine n'est pas disponible en `europe-west9` → on utilise `europe-west1` (UE).

---

## Comment lancer

### Prérequis
```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project regagent-dora-2026
```

### 1. Charger les référentiels DORA/ISO (une seule fois)
```bash
cd fintech-hackathon-2026
python3 data_pipeline/reference/load_reference.py
```

### 2. Démarrer l'API
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

### 3. Uploader un contrat
```bash
curl -X POST http://localhost:8080/api/documents/upload \
  -F "file=@contrat.pdf" \
  -F "vendor_name=AWS"
```

Réponse :
```json
{
  "document_id": "a1b2c3d4",
  "vendor_name": "AWS",
  "status": "extracted",
  "total_clauses": 94,
  "total_sla_entries": 0
}
```

### 4. Swagger
```
http://localhost:8080/docs
```

---

## Catégories DORA détectées automatiquement

Le chunker classe chaque clause dans l'une de ces catégories (basé sur les mots-clés FR/EN) :

| Catégorie | Correspond à |
|---|---|
| `rto_rpo` | RTO, RPO, recovery time, continuité |
| `audit_rights` | audit, inspection, droit de visite |
| `data_residency` | résidence données, localisation, hébergement |
| `subcontracting` | sous-traitant, fourth party |
| `incident_reporting` | incident, notification, breach |
| `exit_strategy` | exit, résiliation, portabilité |
| `general` | tout le reste |

---

## Ce qui est déjà dans le corpus RAG

- **24 contrats vendeurs** indexés (depuis `gs://regagent-documents-eu/`)
- **DORA Art. 30** — 8 articles (depuis `reference_data/dora_article_30.json`)
- **ISO 27001** — 7 contrôles (depuis `reference_data/iso27001_controls.json`)
- **Règles banque** — 8 règles internes (depuis `reference_data/bank_rules_sample.json`)

Total : ~2 250 chunks dans le corpus.

---

## Prochaine étape : EvaluatorAgent

`app/agents/evaluator.py` — prendre une exigence DORA, requêter le corpus, passer à Gemini pour classification `compliant / partial / non_compliant` + score 0–1.

Les prompts Gemini sont déjà écrits dans `app/agents/prompts.py` (`CLASSIFICATION_PROMPT`, `GAP_ANALYSIS_PROMPT`).
