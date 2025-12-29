@echo off
REM Instant deploy - only deploy, no rebuild
REM Use this when you only changed Python code, not dependencies

echo Deploying latest image instantly...

gcloud run deploy quendoo-mcp-server ^
  --image=gcr.io/quendoo-mcp-prod/quendoo-mcp-server:latest ^
  --project=quendoo-mcp-prod ^
  --region=us-central1 ^
  --platform=managed ^
  --allow-unauthenticated ^
  --quiet

echo Done in ~10 seconds!
