#!/usr/bin/env bash
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
PROJECT=gen-lang-client-0704112831
REGION=us-central1
BACKEND_SVC=dora-backend
FRONTEND_SVC=dora-frontend
BACKEND_IMAGE="gcr.io/$PROJECT/$BACKEND_SVC"
FRONTEND_IMAGE="gcr.io/$PROJECT/$FRONTEND_SVC"

# Load secrets from .env
source <(grep -v '^#' .env | grep -v '^$' | sed 's/^/export /')

# ── Backend: build + push ────────────────────────────────────────────────────
echo "🔨 Building backend image…"
docker build -t "$BACKEND_IMAGE" .
docker push "$BACKEND_IMAGE"

# Inject the real image URL into the Cloud Run YAML and deploy
# (Neo4j runs as a sidecar — no external Neo4j account needed)
echo "🚀 Deploying backend + Neo4j sidecar to Cloud Run…"
sed \
  -e "s|BACKEND_IMAGE_PLACEHOLDER|$BACKEND_IMAGE|g" \
  -e "s|CEREBRAS_API_KEY_PLACEHOLDER|${CEREBRAS_API_KEY}|g" \
  -e "s|GEMINI_API_KEY_PLACEHOLDER|${GEMINI_API_KEY}|g" \
  cloud-run-backend.yaml | \
  gcloud run services replace - \
    --region "$REGION" \
    --platform managed

gcloud run services add-iam-policy-binding "$BACKEND_SVC" \
  --region "$REGION" \
  --member="allUsers" \
  --role="roles/run.invoker" 2>/dev/null || true

BACKEND_URL=$(gcloud run services describe "$BACKEND_SVC" \
  --region "$REGION" \
  --format "value(status.url)")
echo "✅ Backend: $BACKEND_URL"

# ── Frontend: build + push + deploy ──────────────────────────────────────────
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
