# Makefile for Dependency Analysis Service

.PHONY: help build up down logs test clean setup

# Default target
help:
	@echo "Available commands:"
	@echo "  make setup     - Set up the development environment"
	@echo "  make build     - Build Docker images"
	@echo "  make up        - Start services with Docker Compose"
	@echo "  make down      - Stop and remove containers"
	@echo "  make logs      - View container logs"
	@echo "  make test      - Run tests against the service"
	@echo "  make clean     - Clean up containers and volumes"
	@echo "  make local     - Set up local Python environment"

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f dependency-analyzer

test:
	python3 test.py

clean:
	docker-compose down -v
	docker system prune -f

# Setup (tries Docker first, falls back to local)
setup:
	@if command -v docker >/dev/null 2>&1; then \
		echo "🐳 Docker detected, setting up with Docker..."; \
		make build && make up; \
	else \
		echo "⚠️  Docker not found, setting up local environment..."; \
		make local; \
	fi

# Local Python setup
local:
	@echo "Setting up local Python environment..."
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
	@echo "✅ Local environment ready!"
	@echo "To activate: source venv/bin/activate"
	@echo "To run: python main.py"

# Development commands
dev-up:
	docker-compose -f docker-compose.yml up --build -d

prod-up:
	docker-compose -f docker-compose.prod.yml up --build -d

# Health check
health:
	@curl -f http://localhost:5003/health || echo "Service not responding"

# Run a quick test
quick-test:
	@echo "Running quick health check..."
	@make health