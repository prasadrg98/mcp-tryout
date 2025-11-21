# Use a lightweight OpenJDK image that includes both Java and common build tools
FROM openjdk:17-jdk-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV GRADLE_VERSION=8.4
ENV PATH="/opt/gradle/gradle-${GRADLE_VERSION}/bin:${PATH}"

# Install system dependencies and Gradle in a single layer
RUN apt-get update && \
    apt-get install -y \
    ca-certificates \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && wget -q https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip -O /tmp/gradle.zip \
    && unzip -q /tmp/gradle.zip -d /opt/gradle \
    && rm /tmp/gradle.zip

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install Python dependencies
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY test.py .
COPY README.md .

# Create directory for temporary repositories
RUN mkdir -p /app/temp_repos

# Expose port
EXPOSE 5003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5003/health || exit 1

# Run the application
CMD ["python", "main.py"]