#!/bin/bash
# Quick deployment script for Quendoo MCP with OAuth

set -e

echo "==================================="
echo "Quendoo MCP OAuth Deployment Script"
echo "==================================="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found. Please install it first."
    exit 1
fi

# Prompt for configuration
read -p "Enter your Google Cloud project ID: " PROJECT_ID
read -p "Enter your PostgreSQL DATABASE_URL: " DATABASE_URL
read -sp "Enter JWT_SECRET (press Enter to generate): " JWT_SECRET
echo ""
read -sp "Enter FLASK_SECRET_KEY (press Enter to generate): " FLASK_SECRET_KEY
echo ""
read -p "Enter EMAIL_API_KEY: " EMAIL_API_KEY
read -p "Enter QUENDOO_AUTOMATION_BEARER: " QUENDOO_AUTOMATION_BEARER

# Generate secrets if not provided
if [ -z "$JWT_SECRET" ]; then
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "✅ Generated JWT_SECRET: $JWT_SECRET"
fi

if [ -z "$FLASK_SECRET_KEY" ]; then
    FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "✅ Generated FLASK_SECRET_KEY: $FLASK_SECRET_KEY"
fi

echo ""
echo "📦 Step 1: Deploying Auth Server..."
gcloud run deploy quendoo-mcp-auth \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars "DATABASE_URL=$DATABASE_URL,JWT_SECRET=$JWT_SECRET,FLASK_SECRET_KEY=$FLASK_SECRET_KEY" \
    --platform managed \
    --project "$PROJECT_ID" \
    --dockerfile Dockerfile.auth

AUTH_URL=$(gcloud run services describe quendoo-mcp-auth --region us-central1 --format="value(status.url)" --project "$PROJECT_ID")
echo "✅ Auth server deployed at: $AUTH_URL"

echo ""
echo "📦 Step 2: Deploying MCP Server..."
gcloud run deploy quendoo-mcp-server \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars "DATABASE_URL=$DATABASE_URL,JWT_SECRET=$JWT_SECRET,EMAIL_API_KEY=$EMAIL_API_KEY,QUENDOO_AUTOMATION_BEARER=$QUENDOO_AUTOMATION_BEARER,AUTH_ISSUER_URL=$AUTH_URL,AUTH_RESOURCE_URL=https://quendoo-mcp-server-851052272168.us-central1.run.app" \
    --platform managed \
    --project "$PROJECT_ID"

MCP_URL=$(gcloud run services describe quendoo-mcp-server --region us-central1 --format="value(status.url)" --project "$PROJECT_ID")
echo "✅ MCP server deployed at: $MCP_URL"

echo ""
echo "==================================="
echo "✅ Deployment Complete!"
echo "==================================="
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Register at: $AUTH_URL/register"
echo "2. Copy your JWT token"
echo "3. Add to claude_desktop_config.json:"
echo ""
echo '{'
echo '  "mcpServers": {'
echo '    "quendoo-pms": {'
echo "      \"url\": \"$MCP_URL/sse\","
echo '      "headers": {'
echo '        "Authorization": "Bearer YOUR_JWT_TOKEN_HERE"'
echo '      }'
echo '    }'
echo '  }'
echo '}'
echo ""
echo "4. Restart Claude Desktop"
echo ""
echo "🔒 Save these secrets securely:"
echo "JWT_SECRET: $JWT_SECRET"
echo "FLASK_SECRET_KEY: $FLASK_SECRET_KEY"
