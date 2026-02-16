#!/bin/bash
# Quick start script for running Evo MCP in Docker

set -e

echo "🐳 Evo MCP Docker Quick Start"
echo "================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please configure your Evo credentials in .env"
    echo "   Edit the file and fill in EVO_CLIENT_ID and other required variables."
    exit 0
fi

# Check if credentials are filled in
if grep -q "your-client-id-here" .env; then
    echo "❌ Please configure your Evo credentials in .env"
    echo "   Set EVO_CLIENT_ID to your actual client ID"
    exit 1
fi

echo "✅ Environment file configured"
echo ""
echo "Building Docker image..."
docker-compose build

echo ""
echo "Starting Evo MCP server..."
docker-compose up -d

echo ""
echo "✅ Evo MCP is running!"
echo ""
echo "📋 Container name: evo-mcp-server"
echo "📊 View logs:      docker-compose logs -f evo-mcp"
echo "🛑 Stop server:    docker-compose down"
echo "🔄 Rebuild:        docker-compose build --no-cache"
echo ""
echo "For more info, see DOCKER-SETUP.md"
