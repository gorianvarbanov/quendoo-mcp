#!/usr/bin/env python3
"""
Ultra-fast deployment script.
Uses gcloud builds submit + deploy in optimal sequence.
Target: <30 seconds total deployment time.
"""

import subprocess
import sys
import time
import os

PROJECT_ID = "quendoo-mcp-prod"
REGION = "us-central1"
SERVICE_NAME = "quendoo-mcp-server"
IMAGE = f"gcr.io/{PROJECT_ID}/{SERVICE_NAME}"


def run_command(cmd, description):
    """Run a command and show output."""
    print(f"\n{'='*60}")
    print(f"⚡ {description}")
    print(f"{'='*60}")
    start = time.time()

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            text=True,
            capture_output=False
        )
        elapsed = time.time() - start
        print(f"✅ {description} completed in {elapsed:.1f}s")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False


def main():
    """Main deployment function."""
    total_start = time.time()

    print("🚀 Starting ultra-fast deployment...")
    print(f"   Project: {PROJECT_ID}")
    print(f"   Region: {REGION}")
    print(f"   Service: {SERVICE_NAME}")

    # Step 1: Build Docker image (with caching)
    build_cmd = f"""
    gcloud builds submit \
      --tag {IMAGE} \
      --project={PROJECT_ID} \
      --region={REGION} \
      --machine-type=E2_HIGHCPU_8 \
      --timeout=5m \
      --quiet
    """

    if not run_command(build_cmd, "Building Docker image"):
        sys.exit(1)

    # Step 2: Deploy to Cloud Run
    deploy_cmd = f"""
    gcloud run deploy {SERVICE_NAME} \
      --image={IMAGE} \
      --project={PROJECT_ID} \
      --region={REGION} \
      --platform=managed \
      --allow-unauthenticated \
      --timeout=300 \
      --concurrency=80 \
      --max-instances=10 \
      --min-instances=0 \
      --memory=512Mi \
      --cpu=1 \
      --quiet
    """

    if not run_command(deploy_cmd, "Deploying to Cloud Run"):
        sys.exit(1)

    total_elapsed = time.time() - total_start

    print(f"\n{'='*60}")
    print(f"✅ DEPLOYMENT COMPLETE!")
    print(f"{'='*60}")
    print(f"⏱️  Total time: {total_elapsed:.1f} seconds")
    print(f"🌐 Service URL: https://{SERVICE_NAME}-851052272168.{REGION}.run.app")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
