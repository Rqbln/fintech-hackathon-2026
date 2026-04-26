#!/usr/bin/env bash
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
PROJECT=gen-lang-client-0704112831
REGION=us-central1
BACKEND_SVC=dora-backend
FRONTEND_SVC=dora-frontend
BACKEND_IMAGE="gcr.io/$PROJECT/$BACKEND_SVC"
FRONTEND_IMAGE="gcr.io/$PROJECT/$FRONTEND_SVC"

# Load secrets from .env (skip comments and empty lines)
source <(grep -v '^#' .env | grep -v '^$' | sed 's/^/export /')

echo "🔨 Building backend image…"
docker build -t "$BACKEND_IMAGE" .
docker push "$BACKEND_IMAGE"

echo "🚀 Deploying backend to Cloud Run…"
gcloud run deploy "$BACKEND_SVC" \
  --image "$BACKEND_IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars "\
LLM_PROVIDER=${LLM_PROVIDER:-cerebras},\
CEREBRAS_API_KEY=${CEREBRAS_API_KEY},\
CEREBRAS_MODEL=${CEREBRAS_MODEL:-llama3.1-8b},\
GEMINI_API_KEY=${GEMINI_API_KEY},\
GCP_PROJECT=${GCP_PROJECT},\
GCP_REGION=${GCP_REGION:-us-central1},\
GCS_BUCKET=${GCS_BUCKET},\
VERTEX_AI_VS_COLLECTION=${VERTEX_AI_VS_COLLECTION:-dora-analyst-docs},\
VERTEX_AI_VS_ENDPOINT_ID=${VERTEX_AI_VS_ENDPOINT_ID},\
NEO4J_URI=${NEO4J_URI},\
NEO4J_USER=${NEO4J_USER:-neo4j},\
NEO4J_PASSWORD=${NEO4J_PASSWORD},\
LOG_LEVEL=INFO"

BACKEND_URL=$(gcloud run services describe "$BACKEND_SVC" \
  --region "$REGION" \
  --format "value(status.url)")
echo "✅ Backend: $BACKEND_URL"

echo "🔨 Building frontend image (BACKEND_URL=$BACKEND_URL)…"
docker build \
  --build-arg BACKEND_URL="$BACKEND_URL" \
  -t "$FRONTEND_IMAGE" \
  frontend/
docker push "$FRONTEND_IMAGE"

echo "🚀 Deploying frontend to Cloud Run…"
gcloud run deploy "$FRONTEND_SVC" \
  --image "$FRONTEND_IMAGE" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --set-env-vars "BACKEND_URL=$BACKEND_URL"

FRONTEND_URL=$(gcloud run services describe "$FRONTEND_SVC" \
  --region "$REGION" \
  --format "value(status.url)")

echo ""
echo "✅ Done."
echo "   Frontend → $FRONTEND_URL"
echo "   Backend  → $BACKEND_URL"
