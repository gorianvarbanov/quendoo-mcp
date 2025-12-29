#!/bin/bash
# Fast deployment script for Quendoo MCP Server

set -e

PROJECT_ID="quendoo-mcp-prod"
REGION="us-central1"
SERVICE_NAME="quendoo-mcp-server"

echo "🚀 Starting optimized deployment..."

# Build and deploy using Cloud Build (faster than gcloud run deploy --source)
gcloud builds submit \
  --project=$PROJECT_ID \
  --region=$REGION \
  --tag gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --timeout=10m

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --project=$PROJECT_ID \
  --region=$REGION \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --allow-unauthenticated \
  --timeout=300 \
  --max-instances=10 \
  --min-instances=0 \
  --memory=512Mi \
  --cpu=1

echo "✅ Deployment complete!"
echo "URL: https://quendoo-mcp-server-880871219885.us-central1.run.app"
