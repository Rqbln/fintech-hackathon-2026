# RegAgent -- Guide de Démarrage

## Prérequis

| Outil | Version | Installation |
|-------|---------|-------------|
| Python | 3.12+ | `brew install python@3.12` |
| Node.js | 20+ | `brew install node` |
| Docker | 24+ | [Docker Desktop](https://www.docker.com/products/docker-desktop/) |
| gcloud CLI | 545+ | [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) |
| Git | 2.40+ | `brew install git` |

## Configuration GCP

### 1. Authentification

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project regagent-dora-2026
gcloud config set compute/region europe-west9
```

### 2. Vérifier l'accès Gemini

```bash
curl -s -X POST \
  "https://europe-west1-aiplatform.googleapis.com/v1/projects/regagent-dora-2026/locations/europe-west1/publishers/google/models/gemini-2.5-flash:generateContent" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"role":"user","parts":[{"text":"Say OK"}]}]}'
```

Réponse attendue : `"text": "OK"`

### 3. Variables d'environnement

```bash
cp .env.example .env
```

Éditer `.env` et remplir les valeurs manquantes (Vector Search IDs après création de l'index).

## Backend (FastAPI)

### Installation locale

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Lancer le serveur

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

API accessible sur `http://localhost:8080`
Documentation OpenAPI : `http://localhost:8080/docs`

### Docker

```bash
cd backend
docker build -t regagent-backend .
docker run -p 8080:8080 \
  -e GCP_PROJECT=regagent-dora-2026 \
  -e GEMINI_MODEL=gemini-2.5-flash \
  regagent-backend
```

## Frontend (React)

### Installation

```bash
cd frontend
npm install
```

### Développement

```bash
npm run dev
```

App accessible sur `http://localhost:5173`
Les appels `/api/*` sont proxifiés vers le backend sur le port 8080.

### Build production

```bash
npm run build
```

### Docker

```bash
cd frontend
docker build -t regagent-frontend .
docker run -p 3000:80 regagent-frontend
```

## Pipeline de Données

### Charger le référentiel dans Vector Search

> **Prérequis** : un index Vertex AI Vector Search doit être créé et déployé.

```bash
cd data_pipeline
python -m reference.load_reference
```

### Tester l'extraction Document AI

```bash
cd data_pipeline
python -m ingestion.extract_text --file ../docs/sample.pdf
```

## Déploiement Cloud Run

### Backend

```bash
cd backend
gcloud builds submit --tag europe-west9-docker.pkg.dev/regagent-dora-2026/regagent-repo/backend:latest

gcloud run deploy regagent-backend \
  --image europe-west9-docker.pkg.dev/regagent-dora-2026/regagent-repo/backend:latest \
  --region europe-west9 \
  --service-account regagent-runtime-sa@regagent-dora-2026.iam.gserviceaccount.com \
  --set-env-vars GCP_PROJECT=regagent-dora-2026,GEMINI_MODEL=gemini-2.5-flash \
  --allow-unauthenticated
```

### Frontend

```bash
cd frontend
gcloud builds submit --tag europe-west9-docker.pkg.dev/regagent-dora-2026/regagent-repo/frontend:latest

gcloud run deploy regagent-frontend \
  --image europe-west9-docker.pkg.dev/regagent-dora-2026/regagent-repo/frontend:latest \
  --region europe-west9 \
  --allow-unauthenticated
```

## Clé API Gemini (Generative Language API)

Pour le développement local sans credentials GCP, une clé API est disponible :

```bash
export GEMINI_API_KEY="AIzaSyAMXHiamVrKqyk13nLBWkWKaLhbyR7vqPk"
```

Cette clé est restreinte au service `generativelanguage.googleapis.com` uniquement.

**Endpoint alternatif** (Google AI Studio, sans Vertex AI) :

```bash
curl -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Test"}]}]}'
```

## Commandes Utiles

```bash
# Lister les services GCP activés
gcloud services list --enabled --project=regagent-dora-2026

# Vérifier le billing
gcloud billing projects describe regagent-dora-2026

# Voir les logs Cloud Run
gcloud run services logs read regagent-backend --region=europe-west9

# Uploader des fichiers vers GCS
gsutil cp reference_data/*.json gs://regagent-reference-eu/
```

## Troubleshooting

| Problème | Solution |
|----------|----------|
| Gemini retourne 404 | Vérifier que le modèle est `gemini-2.5-flash` (pas 1.5 ou 2.0) |
| Document AI "Invalid choice" | Utiliser l'API REST au lieu de gcloud CLI |
| Cloud Run permission denied | Vérifier les rôles du service account `regagent-runtime-sa` |
| Vector Search timeout | L'index prend ~30 min à se créer et déployer |
| Frontend ne se build pas | Vérifier que `tsconfig.json`, `vite.config.ts`, `index.html` existent |
