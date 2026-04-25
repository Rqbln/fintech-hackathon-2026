# RegAgent — Pipeline d'analyse documentaire

## Ce qui fonctionne aujourd'hui

### Vue d'ensemble

```
PDF (GCS)
   │
   ▼
Document AI (OCR)          ← Google Cloud Document AI EU
   │
   ▼
Chunker (LangChain)        ← Découpage par clauses juridiques + classification
   │
   ▼
Vertex AI Embeddings       ← text-multilingual-embedding-002 (768 dims)
   │
   ▼
Vector Store               ← Firestore (prod) ou RAM (dev)
   │
   ▼
Cosine Similarity Search   ← Filtre par doc_id, retourne page + score
```

---

## Composants implémentés

### 1. Document AI — OCR (`backend/app/services/document_ai.py`)

- Appelle Google Cloud Document AI (processor `9a4312989d6fb591`, région EU)
- Gère automatiquement les PDFs > 15 pages en les découpant en chunks (limite du processor)
- Retourne un dict structuré : `{ total_pages, pages_text: [{page, text}], tables: [{page, headers, rows}] }`
- Détecte les tableaux SLA (RTO/RPO) quand ils sont structurés

### 2. Chunker (`backend/app/utils/chunker.py`)

- Utilise `LangChain RecursiveCharacterTextSplitter` avec des séparateurs juridiques FR/EN
- Séparateurs : `Article X`, `Section X`, `Clause X`, `X.X`, numéros de paragraphes
- Chunk size : 800 caractères, overlap : 100
- Classifie automatiquement chaque chunk en 7 catégories DORA :
  - `rto_rpo` — continuité, RTO, RPO, disponibilité
  - `audit_rights` — droits d'audit, inspection
  - `data_residency` — localisation données, hébergement
  - `subcontracting` — sous-traitants, fourth-party
  - `incident_reporting` — incidents, notifications, breach
  - `exit_strategy` — résiliation, portabilité, sortie
  - `general` — tout le reste

### 3. Vertex AI Embeddings (`backend/app/services/vertex_ai.py`)

- Modèle : `text-multilingual-embedding-002` (multilingue FR/EN)
- Dimensions : 768 par chunk
- Appelle l'API Vertex AI dans `europe-west9`

### 4. Vector Store (`backend/app/services/vector_store.py`)

Deux backends contrôlés par la variable d'environnement `VECTOR_STORE_BACKEND` :

| Backend | Variable | Usage | Persistance |
|---------|----------|-------|-------------|
| Memory | `memory` (défaut) | Dev local | Non — perdu au redémarrage |
| Firestore | `firestore` | Production | Oui — GCP Firestore `eur3` |

Chaque entrée stockée contient :
```
chunk_id    : "{doc_id}_{page}_{chunk_index}"
doc_id      : identifiant unique du contrat
vendor_name : nom du fournisseur
text        : texte de la clause
page        : numéro de page dans le PDF original
category    : rto_rpo | audit_rights | data_residency | ...
embedding   : [768 floats] — JSON string dans Firestore
```

Recherche : **cosine similarity** avec filtre optionnel par `doc_id`.
Scores observés sur contrats réels : **0.75 – 0.83** (vs 0.32–0.39 avec Vertex AI RAG Engine).

### 5. Agent Extracteur (`backend/app/agents/extractor.py`)

Pipeline complet en une seule méthode `extract()` :
1. Upload PDF dans GCS (`uploads/{doc_id}_{filename}`)
2. OCR via Document AI
3. Chunking + classification
4. Embedding de tous les chunks
5. Upsert dans le Vector Store
6. Retourne un `VendorDocument` Pydantic avec clauses, SLA entries, GCS URI

Méthode de recherche `search(query, doc_id, top_k)` :
1. Embed la query
2. Recherche cosine dans le store filtré par doc_id
3. Retourne les N chunks les plus proches avec score + page

### 6. API REST (`backend/app/routers/documents.py`)

| Endpoint | Description |
|----------|-------------|
| `POST /api/documents/upload` | Upload 1 PDF — traitement synchrone |
| `POST /api/documents/upload/batch` | Upload N PDFs — traitement séquentiel en background |
| `GET /api/documents/upload/batch/{batch_id}` | Poll le statut du batch |
| `GET /api/documents/` | Liste tous les documents indexés |
| `GET /api/documents/{document_id}` | Détails d'un document |

Le batch traite les fichiers **un par un dans l'ordre** — le fichier 2 ne démarre pas avant que le fichier 1 soit entièrement traité (OCR + embed + indexé).

---

## Infrastructure GCP utilisée

| Service GCP | Usage | Région |
|-------------|-------|--------|
| Cloud Storage `regagent-documents-eu` | Stockage PDFs originaux | europe-west9 (Paris) |
| Document AI `9a4312989d6fb591` | OCR des PDFs | EU |
| Vertex AI `text-multilingual-embedding-002` | Calcul embeddings | europe-west9 |
| Firestore `(default)` | Persistance vecteurs | eur3 (Europe) |
| Cloud Run (à déployer) | Hébergement FastAPI | europe-west9 |

---

## Performances observées sur contrats réels

Tests effectués sur `contrat_20_cloud_computing.pdf` (229 KB, 40 pages) :

| Query | Score cosine | Page | Catégorie trouvée |
|-------|-------------|------|-------------------|
| "RTO temps de reprise service critique" | 0.759 | p5 | rto_rpo |
| "droit audit inspection fournisseur" | 0.830 | p8 | rto_rpo |
| "localisation données hébergement" | 0.758 | p6 | data_residency |
| "incident notification breach" | 0.705 | p30 | audit_rights |

---

## Ce qui n'est pas encore implémenté

| Composant | Fichier | Statut |
|-----------|---------|--------|
| Agent Évaluateur (Gemini) | `agents/evaluator.py` | Stub vide |
| Agent Orchestrateur | `agents/orchestrator.py` | Stub vide |
| Génération d'avenants | — | Non démarré |
| Export rapport PDF | — | Non démarré |

---

## Lancer le projet en local

```bash
# Variables d'environnement
export GOOGLE_APPLICATION_CREDENTIALS="$APPDATA/gcloud/application_default_credentials.json"
export GCP_PROJECT="regagent-dora-2026"
export VECTOR_STORE_BACKEND="memory"   # ou "firestore" pour persister

# Démarrer le backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# API disponible sur http://localhost:8000/docs
```

## Basculer en Firestore (production)

Une seule variable à changer :
```bash
export VECTOR_STORE_BACKEND="firestore"
```

Le reste du code ne change pas.
