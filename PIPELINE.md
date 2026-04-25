# RegAgent — Pipeline d'analyse documentaire

## Vue d'ensemble — Pipeline complet

```
PDF (GCS)
   │
   ▼
Document AI (OCR)               ← Google Cloud Document AI EU
   │
   ▼
Chunker (LangChain)             ← Découpage par clauses juridiques + classification DORA
   │
   ▼
Vertex AI Embeddings            ← text-multilingual-embedding-002 (768 dims)
   │
   ▼
Vector Store                    ← Firestore (prod) ou RAM (dev)
   │
   ▼
Cosine Similarity Search        ← Filtre par doc_id, retourne page + score (0.75–0.83)
   │
   ▼
Gemini 2.5 Flash                ← Prompt dynamique : clause + exigence DORA + règle banque
   │
   ▼
Score conformité 0-100          ← Pondéré par criticité DORA (critical x3, high x2)
+ Alertes structurées           ← titre, sévérité, gap, page, action corrective
```

---

## Composants implémentés

### 1. Document AI — OCR (`backend/app/services/document_ai.py`)

- Appelle Google Cloud Document AI (processor `9a4312989d6fb591`, région EU)
- Gère automatiquement les PDFs > 15 pages (split automatique, limite processor)
- Retourne : `{ total_pages, pages_text: [{page, text}], tables: [{page, headers, rows}] }`
- Détecte les tableaux SLA structurés (RTO/RPO)

### 2. Chunker (`backend/app/utils/chunker.py`)

- `LangChain RecursiveCharacterTextSplitter` avec séparateurs juridiques FR/EN
- Séparateurs : `Article X`, `Section X`, `Clause X`, `X.X`, numéros de paragraphes
- Chunk size : 800 caractères, overlap : 100
- Classification automatique en 7 catégories DORA :
  - `rto_rpo` — continuité, RTO, RPO, disponibilité
  - `audit_rights` — droits d'audit, inspection
  - `data_residency` — localisation données, hébergement
  - `subcontracting` — sous-traitants, fourth-party
  - `incident_reporting` — incidents, notifications, breach
  - `exit_strategy` — résiliation, portabilité, sortie
  - `general` — reste

### 3. Vertex AI Embeddings (`backend/app/services/vertex_ai.py`)

- Modèle : `text-multilingual-embedding-002` (multilingue FR/EN)
- 768 dimensions par chunk
- Région : `europe-west9`

### 4. Vector Store (`backend/app/services/vector_store.py`)

Deux backends via variable d'environnement `VECTOR_STORE_BACKEND` :

| Backend | Variable | Usage | Persistance |
|---------|----------|-------|-------------|
| Memory | `memory` (défaut) | Dev local | Non |
| Firestore | `firestore` | Production | Oui — GCP Firestore `eur3` |

Chaque entrée :
```
chunk_id    : "{doc_id}_{page}_{chunk_index}"
doc_id      : identifiant unique du contrat
vendor_name : nom du fournisseur
text        : texte de la clause
page        : numéro de page PDF (pour autoscroll)
category    : rto_rpo | audit_rights | data_residency | ...
embedding   : [768 floats]
```

Recherche : cosine similarity filtrée par `doc_id`.
Scores observés sur contrats réels : **0.75 – 0.83**.

### 5. Agent Extracteur (`backend/app/agents/extractor.py`)

Méthode `extract(content, filename, vendor_name)` — pipeline complet :
1. Upload PDF dans GCS
2. OCR via Document AI
3. Chunking + classification
4. Embedding Vertex AI
5. Upsert dans le Vector Store (Firestore ou RAM)
6. Retourne `VendorDocument` Pydantic (clauses, SLA entries, GCS URI)

Méthode `search(query, doc_id, top_k)` :
1. Embed la query
2. Cosine similarity filtré par `doc_id`
3. Retourne chunks avec score + page

### 6. Agent Évaluateur (`backend/app/agents/evaluator.py`)

Méthode `evaluate(doc_id, vendor_name)` — moteur de conformité DORA :

**Pour chaque catégorie DORA (6 au total) :**
1. RAG — top-3 chunks les plus pertinents via `search()`
2. Prompt dynamique construit avec :
   - La clause trouvée dans le contrat (avec numéro de page)
   - L'exigence DORA Art. 30 correspondante (`reference_data/dora_article_30.json`)
   - La règle interne banque (`reference_data/bank_rules_sample.json`)
3. Appel Gemini 2.5 Flash en mode JSON strict
4. Résultat : `gap_exists`, `severity`, `title`, `description`, `quantitative_gap`, `recommended_action`

**Calcul du score global :**
- Pondération par criticité DORA : `critical × 3`, `high × 2`, `medium × 1`
- `compliant = 100`, `partial = 50`, `non_compliant = 0`
- Score final normalisé sur 100

**Résultat retourné :**
```json
{
  "doc_id": "...",
  "vendor_name": "...",
  "compliance_score": 38,
  "status": "non_compliant",
  "category_scores": {
    "rto_rpo": 100,
    "audit_rights": 0,
    "data_residency": 50,
    "subcontracting": 50,
    "incident_reporting": 0,
    "exit_strategy": 0
  },
  "alerts": [
    {
      "severity": "high",
      "title": "Missing minimum annual audit frequency",
      "dora_reference": "Art. 30(2)(f)",
      "page": 8,
      "gap_details": "...",
      "remediation": "..."
    }
  ]
}
```

### 7. API REST (`backend/app/routers/documents.py`)

| Endpoint | Description |
|----------|-------------|
| `POST /api/documents/upload` | Upload 1 PDF — synchrone |
| `POST /api/documents/upload/batch` | Upload N PDFs — séquentiel en background |
| `GET /api/documents/upload/batch/{batch_id}` | Poll statut du batch |
| `GET /api/documents/` | Liste documents indexés |
| `GET /api/documents/{document_id}` | Détails d'un document |

Batch : traitement **un fichier à la fois dans l'ordre** — fichier 2 attend que fichier 1 soit entièrement traité.

---

## Résultats observés sur contrats réels

Test sur `contrat_20_cloud_computing.pdf` (229 KB, 40 pages) :

**RAG — scores de recherche :**

| Query | Score cosine | Page | Catégorie |
|-------|-------------|------|-----------|
| RTO temps de reprise | 0.759 | p5 | rto_rpo |
| Droit audit fournisseur | 0.830 | p8 | audit_rights |
| Localisation données | 0.758 | p6 | data_residency |
| Incident notification | 0.705 | p30 | incident_reporting |

**Évaluation DORA — Gemini 2.5 Flash :**

| Catégorie | Score | Statut | Motif |
|-----------|-------|--------|-------|
| RTO/RPO | 100/100 | Conforme | RTO 2h et RPO 15min explicites |
| Audit rights | 0/100 | Non conforme | Pas de fréquence annuelle garantie |
| Data residency | 50/100 | Partiel | Clause de transfert légal ambiguë |
| Subcontracting | 50/100 | Partiel | Pas de liste proactive des sous-traitants |
| Incident reporting | 0/100 | Non conforme | Délai RCA non défini, "sans délai indu" trop vague |
| Exit strategy | 0/100 | Non conforme | Portabilité 90j absente, transition contradictoire |

**Score global : 38/100 — NON COMPLIANT**
**5 alertes générées** avec page, gap quantitatif et action corrective.

---

## Infrastructure GCP

| Service | Usage | Région |
|---------|-------|--------|
| Cloud Storage `regagent-documents-eu` | PDFs originaux | europe-west9 (Paris) |
| Document AI `9a4312989d6fb591` | OCR | EU |
| Vertex AI `text-multilingual-embedding-002` | Embeddings | europe-west9 |
| Gemini 2.5 Flash | Évaluation conformité | europe-west9 |
| Firestore `(default)` | Persistance vecteurs | eur3 (Europe) |
| Cloud Run (à déployer) | API FastAPI | europe-west9 |

---

## Ce qui reste à implémenter

| Composant | Fichier | Statut |
|-----------|---------|--------|
| Endpoint `/api/analysis/{doc_id}` | `routers/analysis.py` | À faire |
| Agent Orchestrateur (concentration risk) | `agents/orchestrator.py` | Stub vide |
| Connexion frontend → backend | `src/components/*.tsx` | À faire |
| Split-Screen + autoscroll | `GapAnalysis.tsx` | À faire |
| Génération d'avenants | — | Non démarré |
| Export rapport PDF | — | Non démarré |

---

## Lancer en local

```bash
export GOOGLE_APPLICATION_CREDENTIALS="$APPDATA/gcloud/application_default_credentials.json"
export GCP_PROJECT="regagent-dora-2026"
export VECTOR_STORE_BACKEND="memory"   # ou "firestore" pour persister

cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Swagger UI : http://localhost:8000/docs
```

## Basculer Firestore (prod)

```bash
export VECTOR_STORE_BACKEND="firestore"
# Rien d'autre ne change.
```
