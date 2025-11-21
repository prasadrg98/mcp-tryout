# Dependency Analysis Service

FastAPI service for analyzing Gradle dependencies in GitHub repositories with Docker support for isolated testing.

## Features

- **Repository Cloning**: Download and analyze any public GitHub repository
- **Gradle Detection**: Automatically find all Gradle build files (build.gradle, build.gradle.kts)
- **Dependency Analysis**: Run `gradle dependencies` for each configuration
- **Pattern Matching**: Find target dependencies and extract parent version information
- **Isolated Environment**: Docker support with pre-installed Java, Gradle, and Python dependencies
- **RESTful API**: Clean REST API with async processing and status polling
- **Health Monitoring**: Built-in health checks and comprehensive logging

## Quick Start

### Automated Setup (Recommended)

Use the Makefile for the easiest setup experience:

```bash
# Clone and navigate to the service directory
cd dependency-analysis-service

# Automatically detect and set up environment (Docker or local)
make setup

# Run tests
make test

# View all available commands
make help
```

### Option 1: Docker (Recommended if Docker is available)

```bash
# Build and start the service
make up
# OR manually:
docker-compose up --build -d

# Run tests
make test

# View logs
make logs

# Stop service
make down
```

### Option 2: Local Development

```bash
# Set up local environment
make local
# OR manually:
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# Start service
./service.sh start

# Run tests
python3 test_comprehensive.py

# Check status
./service.sh status
```

### Option 3: Production Service Management

```bash
# Production-ready service management
./service.sh start    # Start service
./service.sh status   # Check status
./service.sh logs     # View logs
./service.sh logs -f  # Follow logs
./service.sh restart  # Restart service
./service.sh stop     # Stop service
./service.sh health   # Health check
```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Gradle (if not already installed)
# On macOS:
brew install gradle

# On Ubuntu/Debian:
sudo apt install gradle

# Or use SDKMAN:
curl -s "https://get.sdkman.io" | bash
sdk install gradle
```

## Usage

```bash
# Start the service
python main.py
```

The service will be available at `http://localhost:5003`

## Configuration

Copy the environment template and customize as needed:

```bash
cp .env.example .env
# Edit .env file with your configuration
```

Key configuration options:
- `PORT`: Service port (default: 5003)
- `GITHUB_TOKEN`: Optional GitHub token for higher rate limits
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `MAX_ANALYSIS_TIME_SECONDS`: Maximum time for analysis (default: 300)

## API Documentation

Once running, visit `http://localhost:5003/docs` for interactive API documentation.

### Example Request

```bash
curl -X POST "http://localhost:5003/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "prasadrg98/sample",
    "dependency_name": "httpclient",
    "github_token": "optional-for-private-repos"
  }'
```

### Example Response

```json
{
  "job_id": "abc123",
  "status": "processing",
  "check_url": "/status/abc123"
}
```

### Check Status

```bash
curl "http://localhost:5003/status/abc123"
```

### Example Complete Result

```json
{
  "repository": "prasadrg98/sample",
  "dependency_name": "httpclient", 
  "job_id": "abc123",
  "status": "completed",
  "gradle_files_found": [
    "build.gradle",
    "cloudbuilders-common-jdk11.gradle"
  ],
  "matches": [
    {
      "file_path": "cloudbuilders-common-jdk11.gradle",
      "current_version": "4.5.19",
      "parent_dependency": null,
      "parent_version": null,
      "dependency_path": ["org.apache.httpcomponents:httpclient"],
      "line_context": "Line 5: apacheHTTPClientVersion = \"4.5.19\""
    }
  ],
  "analysis_time_seconds": 15.2
}
```

## Architecture

```
Request → FastAPI → Background Task → Analysis Result
                     ├── 1. Clone repo
                     ├── 2. Find gradle files  
                     ├── 3. Run gradle dependencies
                     ├── 4. Parse dependency tree
                     └── 5. Return matches
```

## Configuration

Environment variables:
- `WORK_DIR`: Directory for temporary files (default: `/tmp/gradle_analysis`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

## Dependencies

- FastAPI - Web framework
- Pydantic - Data validation
- aiohttp - Async HTTP client
- subprocess - Gradle command execution
- zipfile - Repository download and extraction