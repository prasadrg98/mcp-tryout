#!/bin/bash

# Setup script for Dependency Analysis Service

set -e

echo "🚀 Setting up Dependency Analysis Service..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

# Function to run docker-compose (handles both v1 and v2)
run_compose() {
    if command -v docker-compose &> /dev/null; then
        docker-compose "$@"
    else
        docker compose "$@"
    fi
}

echo "📦 Building Docker image..."
run_compose build

echo "🔧 Starting services..."
run_compose up -d

echo "⏳ Waiting for service to be ready..."
sleep 10

# Test if service is running
echo "🧪 Testing service health..."
if curl -f http://localhost:5003/health &> /dev/null; then
    echo "✅ Service is running successfully!"
    echo ""
    echo "🔗 Service URL: http://localhost:5003"
    echo "📖 API Documentation: http://localhost:5003/docs"
    echo ""
    echo "📝 To run tests:"
    echo "   python3 test.py"
    echo ""
    echo "🛠️  Useful Docker commands:"
    echo "   View logs: docker-compose logs -f dependency-analyzer"
    echo "   Stop service: docker-compose down"
    echo "   Rebuild: docker-compose build --no-cache"
else
    echo "❌ Service health check failed"
    echo "📋 Checking logs..."
    run_compose logs dependency-analyzer
    exit 1
fi