@echo off
echo ========================================
echo Fast Deployment to Cloud Run
echo ========================================

set PROJECT=quendoo-mcp-prod
set REGION=us-central1
set SERVICE=quendoo-mcp-server
set IMAGE=gcr.io/%PROJECT%/%SERVICE%

echo [1/2] Building Docker image with high-CPU machine...
gcloud builds submit --tag %IMAGE% --project=%PROJECT% --region=%REGION% --machine-type=E2_HIGHCPU_32 --timeout=5m --quiet

if %errorlevel% neq 0 (
    echo Build failed!
    exit /b 1
)

echo [2/2] Deploying to Cloud Run...
gcloud run deploy %SERVICE% --image=%IMAGE% --project=%PROJECT% --region=%REGION% --platform=managed --allow-unauthenticated --quiet

echo ========================================
echo Deployment complete!
echo ========================================
