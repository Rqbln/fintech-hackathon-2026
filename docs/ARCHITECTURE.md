# RegAgent -- Architecture Technique

## Vue d'ensemble

RegAgent suit une architecture **microservices** avec un backend FastAPI, un frontend React, et des services managés GCP. Les trois agents IA communiquent via des appels internes au backend et partagent un index vectoriel commun.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Google Cloud Platform                        │
│                        (regagent-dora-2026)                         │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────────────┐ │
│  │  Cloud Run    │    │  Cloud Run    │    │   Vertex AI            │ │
│  │  (Backend)    │◄──►│  (Frontend)   │    │   - Gemini 2.5 Flash   │ │
│  │  FastAPI      │    │  React+Nginx  │    │   - Text Embeddings    │ │
│  └──────┬───────┘    └──────────────┘    │   - Vector Search      │ │
│         │                                 └───────────┬────────────┘ │
│         │                                             │              │
│  ┌──────▼───────┐    ┌──────────────┐    ┌───────────▼────────────┐ │
│  │ Document AI   │    │ Cloud Storage │    │  Secret Manager        │ │
│  │ (OCR)         │    │ (Buckets)     │    │  (Clés & configs)      │ │
│  └──────────────┘    └──────────────┘    └────────────────────────┘ │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐                               │
│  │ Artifact      │    │ IAM + WIF     │                               │
│  │ Registry      │    │ (CI/CD auth)  │                               │
│  └──────────────┘    └──────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Pipeline de Traitement

### Phase 1 : Ingestion (Extractor Agent)

```
Document PDF
     │
     ▼
Document AI (OCR)
     │  Extraction texte brut + tables
     ▼
Clause-Aware Chunker
     │  Découpage par article/section
     │  Regex: Article \d+, Section \d+, \d+\.\d+
     ▼
Vertex AI Text Embeddings
     │  Modèle: text-multilingual-embedding-002
     │  Dimensions: 768
     │  Batch: max 250 textes/appel
     ▼
Vertex AI Vector Search
     │  Index: DOT_PRODUCT_DISTANCE
     │  Metadata: {source, clause_type, vendor_id}
     ▼
Structured Output (JSON)
     ExtractedClause {
       clause_text, category, sla_values,
       entities, confidence_score
     }
```

### Phase 2 : Évaluation (Evaluator Agent)

```
Clauses Extraites
     │
     ├──► Recherche Sémantique (Vector Search)
     │    → Top-K exigences DORA/ISO similaires
     │
     ├──► Gemini 2.5 Flash (Classification)
     │    Prompt: clause + exigence → {compliant, partial, non_compliant}
     │    Output: JSON structuré avec evidence
     │
     ├──► ISO 27005 Risk Scoring
     │    Score = Impact (criticité fonction) × Probabilité (qualité garantie)
     │    Matrice 5×5, seuils: ≤4, 5-9, 10-15, ≥16
     │
     └──► Concentration Risk Analysis
          Matrice inter-fournisseurs, dépendances partagées
          Score de substituabilité par fournisseur
```

### Phase 3 : Orchestration (Orchestrator Agent)

```
Scores + Clauses + Référentiel
     │
     ├──► Gap Analysis (Gemini 2.5 Flash)
     │    Input: règle interne + garantie contractuelle
     │    Output: gap identifié, sévérité, recommandation
     │
     ├──► Alert Generation
     │    Sévérité: critical, high, medium, low
     │    Human-in-the-loop: validation CRO requise pour critical
     │
     └──► Register of Information (RoI)
          Génération des entrées B_01 à B_07
          Format: JSON → CSV (export)
```

---

## API Backend (FastAPI)

### Endpoints

| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/api/documents/upload` | Upload d'un document PDF |
| `GET` | `/api/documents/{id}` | Récupérer un document uploadé |
| `POST` | `/api/analysis/run/{document_id}` | Lancer l'analyse complète |
| `GET` | `/api/analysis/results/{id}` | Résultats d'analyse |
| `GET` | `/api/alerts` | Liste des alertes (filtrable par sévérité) |
| `PATCH` | `/api/alerts/{id}/validate` | Validation CRO d'une alerte |
| `GET` | `/api/register` | Registre d'Information complet |
| `GET` | `/api/register/export` | Export CSV du RoI |

### Modèles de données (Pydantic)

```python
class ExtractedClause:
    clause_text: str
    category: str           # sla, data_residency, audit_rights, ...
    sla_values: dict | None
    entities: list[str]
    confidence_score: float

class ComplianceMapping:
    clause: ExtractedClause
    dora_requirement: str
    iso_control: str
    status: str             # compliant, partial, non_compliant
    evidence: str
    risk_score: float

class Alert:
    id: str
    vendor_name: str
    severity: str           # critical, high, medium, low
    gap_description: str
    recommendation: str
    dora_article: str
    validated_by_cro: bool

class RegisterEntry:
    model_id: str           # B_01.01, B_02.01, etc.
    entity_data: dict
    vendor_data: dict
    function_mapping: dict
```

---

## Services GCP

### Document AI

- **Processor type** : `OCR_PROCESSOR` (reconnaît texte + tables dans les PDFs)
- **Processor ID** : `9a4312989d6fb591`
- **Location** : `eu` (conformité RGPD)
- **Limites** : 15 pages/appel synchrone, batch pour les gros documents

### Vertex AI -- Gemini 2.5 Flash

- **Endpoint** : `europe-west1-aiplatform.googleapis.com`
- **Modèle** : `gemini-2.5-flash`
- **Utilisation** : classification de conformité, gap analysis, génération RoI
- **Configuration** :
  - Temperature: 0.1 (réponses déterministes)
  - Response MIME type: `application/json` (output structuré)
  - Safety settings: BLOCK_NONE (contenu professionnel)

### Vertex AI -- Text Embeddings

- **Modèle** : `text-multilingual-embedding-002`
- **Dimensions** : 768
- **Batch** : max 250 textes par appel
- **Langues** : FR, EN, DE, NL (multi-juridictionnel)

### Vertex AI -- Vector Search

- **Distance** : `DOT_PRODUCT_DISTANCE`
- **Dimensions** : 768
- **Shards** : 1 (prototype)
- **Metadata filtres** : `source`, `category`, `article_id`

### Cloud Storage

| Bucket | Contenu |
|--------|---------|
| `regagent-documents-eu` | PDFs uploadés par les utilisateurs |
| `regagent-reference-eu` | Référentiel DORA/ISO vectorisé |

---

## Sécurité & CI/CD

### Workload Identity Federation (WIF)

GitHub Actions s'authentifie auprès de GCP sans clé API grâce à la fédération d'identité :

```
GitHub Actions (OIDC Token)
     │
     ▼
GCP Workload Identity Pool (regagent-github-pool)
     │
     ▼
OIDC Provider (github-provider)
     │  Issuer: https://token.actions.githubusercontent.com
     │  Attribut: repository = Rqbln/fintech-hackathon-2026
     ▼
Service Account (github-actions-sa)
     │  Rôles: Cloud Run Admin, Storage Admin, Artifact Registry Writer
     ▼
Cloud Run Deployment
```

### Service Accounts

| Compte | Usage | Rôles |
|--------|-------|-------|
| `github-actions-sa` | CI/CD (GitHub Actions) | Cloud Run Admin, Storage Admin, AR Writer, SA User |
| `regagent-runtime-sa` | Runtime (Cloud Run) | Document AI User, Vertex AI User, Storage Object Admin |

### Workflow de déploiement

```
Push sur `main`
     │
     ▼
GitHub Actions (deploy-backend.yml / deploy-frontend.yml)
     │  1. Authenticate via WIF
     │  2. Build Docker image
     │  3. Push to Artifact Registry
     │  4. Deploy to Cloud Run
     ▼
Cloud Run (europe-west9)
     │  Container serverless
     │  Auto-scaling 0→10 instances
     │  256 Mi → 1 Gi RAM
     ▼
HTTPS endpoint public
```

---

## Frontend (React)

### Composants

| Composant | Route | Fonction |
|-----------|-------|----------|
| `Dashboard` | `/` | KPIs, alertes récentes, jauge de risque global |
| `ContractUpload` | `/upload` | Upload drag-and-drop, barre de progression |
| `GapAnalysis` | `/analysis/:id` | Tableau des gaps par article DORA |
| `RiskMap` | `/risks` | Graphe de dépendances fournisseurs |
| `RegisterView` | `/register` | Tableau RoI avec export CSV |

### Communication avec le backend

```
React App (Vite dev / Nginx prod)
     │
     │  Proxy: /api/* → backend:8080
     │
     ▼
FastAPI Backend
```

---

## Choix Techniques Justifiés

| Décision | Justification |
|----------|---------------|
| **Gemini 2.5 Flash** (vs GPT-4, Claude) | Intégration native GCP, faible coût, pensée avancée, multilingue |
| **FastAPI** (vs Django, Flask) | Async natif, validation Pydantic, OpenAPI automatique |
| **Document AI** (vs Mistral OCR) | Intégration GCP native, conformité EU, extraction de tables |
| **Vector Search** (vs Pinecone, Weaviate) | Service managé GCP, pas de serveur à gérer |
| **Cloud Run** (vs GKE, App Engine) | Serverless, scale-to-zero, paiement à l'usage |
| **React + Vite** (vs Next.js) | Simplicité pour un SPA, HMR rapide |
| **WIF** (vs clés API) | Zero-trust, pas de secret à stocker dans GitHub |
