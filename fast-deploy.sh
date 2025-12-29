#!/bin/bash
# Ultra-fast deployment script
# Uses concurrent operations and minimal waiting

set -e

PROJECT_ID="quendoo-mcp-prod"
REGION="us-central1"
SERVICE_NAME="quendoo-mcp-server"
IMAGE="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "🚀 Fast deployment starting..."

# Build and push in background
echo "📦 Building Docker image..."
gcloud builds submit \
  --tag $IMAGE \
  --project=$PROJECT_ID \
  --region=$REGION \
  --machine-type=E2_HIGHCPU_32 \
  --timeout=5m \
  --async \
  --quiet &

BUILD_PID=$!

# Wait for build
wait $BUILD_PID

echo "🚢 Deploying to Cloud Run..."
# Deploy with minimal output
gcloud run deploy $SERVICE_NAME \
  --image=$IMAGE \
  --project=$PROJECT_ID \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --timeout=300 \
  --concurrency=80 \
  --max-instances=10 \
  --min-instances=1 \
  --memory=512Mi \
  --cpu=2 \
  --cpu-boost \
  --no-traffic \
  --tag=latest \
  --quiet

# Update traffic instantly
gcloud run services update-traffic $SERVICE_NAME \
  --to-latest \
  --project=$PROJECT_ID \
  --region=$REGION \
  --quiet

echo "✅ Deployment complete! (~30 seconds total)"
echo "Service: https://quendoo-mcp-server-851052272168.us-central1.run.app"
