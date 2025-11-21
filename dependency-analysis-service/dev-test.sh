#!/bin/bash

# Development script for testing the Dependency Analysis Service

set -e

echo "🧪 Running Dependency Analysis Service Tests"

# Function to run docker-compose (handles both v1 and v2)
run_compose() {
    if command -v docker-compose &> /dev/null; then
        docker-compose "$@"
    else
        docker compose "$@"
    fi
}

# Check if service is running
if ! curl -f http://localhost:5003/health &> /dev/null; then
    echo "⚠️  Service is not running. Starting it now..."
    run_compose up -d
    
    echo "⏳ Waiting for service to be ready..."
    max_attempts=30
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:5003/health &> /dev/null; then
            echo "✅ Service is ready!"
            break
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ Service failed to start. Checking logs..."
        run_compose logs dependency-analyzer
        exit 1
    fi
fi

echo "🚀 Running tests..."

# Run the test script
if command -v python3 &> /dev/null; then
    python3 test.py
elif command -v python &> /dev/null; then
    python test.py
else
    echo "❌ Python is not installed"
    exit 1
fi

echo "📊 Test completed!"
echo ""
echo "💡 Other useful commands:"
echo "   View logs: docker-compose logs -f dependency-analyzer"
echo "   Stop service: docker-compose down"
echo "   Rebuild and restart: docker-compose up --build -d"