#!/bin/bash
# Instant deployment - only rebuild & deploy (parallel when possible)
# Total time: ~15-20 seconds

set -e

PROJECT_ID="quendoo-mcp-prod"
REGION="us-central1"
SERVICE_NAME="quendoo-mcp-server"

echo "⚡ Instant deployment..."

# Single command: build + deploy
gcloud run deploy $SERVICE_NAME \
  --source . \
  --project=$PROJECT_ID \
  --region=$REGION \
  --allow-unauthenticated \
  --quiet \
  --no-promote \
  2>&1 | grep -E "(Deploying|revision|Service URL|Done)" &

DEPLOY_PID=$!

# Show spinner while deploying
while kill -0 $DEPLOY_PID 2>/dev/null; do
  echo -n "."
  sleep 1
done

wait $DEPLOY_PID

# Promote to 100% traffic instantly
gcloud run services update-traffic $SERVICE_NAME \
  --to-latest \
  --project=$PROJECT_ID \
  --region=$REGION \
  --quiet

echo ""
echo "✅ Done!"
