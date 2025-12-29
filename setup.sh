#!/bin/bash
# Quick setup script for botchat

set -e

echo "🚀 botchat Setup"
echo "=========================="

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    echo "   Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

echo "✅ Docker is ready"

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file..."
    
    # Generate random API key for frontend-backend authentication
    API_KEY=$(openssl rand -hex 32)
    
    cat > .env << EOF
# Auto-generated shared secret (do not change unless you know what you're doing)
API_KEY=$API_KEY

# Optional: Pre-configure AI provider keys here, or add them via Settings UI
# OPENAI_API_KEY=sk-your-key
# GOOGLE_API_KEY=your-key

# Logging level (WARNING, INFO, DEBUG)
LOG_LEVEL=WARNING
EOF
    
    echo "✅ Generated secure API_KEY"
    echo ""
    echo "🎉 Setup complete! Starting application..."
    echo ""
    docker compose up --build
else
    echo "✅ .env already exists"
    echo ""
    echo "Starting application..."
    docker compose up --build
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Open http://localhost:3000 in your browser"
echo "⚙️  Click the gear icon to add your API keys"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
