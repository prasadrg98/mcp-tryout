#!/bin/bash

# Production startup script for Dependency Analysis Service

set -e

# Configuration
SERVICE_NAME="dependency-analysis-service"
VENV_PATH="./venv"
MAIN_SCRIPT="main.py"
PID_FILE="/tmp/${SERVICE_NAME}.pid"
LOG_FILE="/tmp/${SERVICE_NAME}.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Function to check if service is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Function to start the service
start() {
    log "Starting $SERVICE_NAME..."
    
    if is_running; then
        warn "Service is already running (PID: $(cat $PID_FILE))"
        return 0
    fi
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_PATH" ]; then
        log "Virtual environment not found. Creating..."
        python3 -m venv "$VENV_PATH"
        log "Installing dependencies..."
        "$VENV_PATH/bin/pip" install -r requirements.txt
    fi
    
    # Start the service
    log "Launching service..."
    nohup "$VENV_PATH/bin/python" "$MAIN_SCRIPT" > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo $pid > "$PID_FILE"
    
    # Wait a moment and check if it started successfully
    sleep 2
    if is_running; then
        log "Service started successfully (PID: $pid)"
        log "Health check in 3 seconds..."
        sleep 3
        if curl -f http://localhost:5003/health >/dev/null 2>&1; then
            log "✅ Service is healthy and responding"
            log "Service URL: http://localhost:5003"
            log "API Docs: http://localhost:5003/docs"
        else
            warn "Service started but health check failed"
        fi
    else
        error "Failed to start service"
        return 1
    fi
}

# Function to stop the service
stop() {
    log "Stopping $SERVICE_NAME..."
    
    if ! is_running; then
        warn "Service is not running"
        return 0
    fi
    
    local pid=$(cat "$PID_FILE")
    log "Sending TERM signal to process $pid"
    kill "$pid"
    
    # Wait for graceful shutdown
    local count=0
    while [ $count -lt 10 ] && kill -0 "$pid" 2>/dev/null; do
        sleep 1
        count=$((count + 1))
    done
    
    if kill -0 "$pid" 2>/dev/null; then
        warn "Process didn't stop gracefully, sending KILL signal"
        kill -9 "$pid"
    fi
    
    rm -f "$PID_FILE"
    log "Service stopped"
}

# Function to restart the service
restart() {
    log "Restarting $SERVICE_NAME..."
    stop
    sleep 1
    start
}

# Function to show service status
status() {
    if is_running; then
        local pid=$(cat "$PID_FILE")
        log "Service is running (PID: $pid)"
        
        # Health check
        if curl -f http://localhost:5003/health >/dev/null 2>&1; then
            log "✅ Health check: OK"
        else
            warn "❌ Health check: FAILED"
        fi
    else
        log "Service is not running"
    fi
}

# Function to show logs
logs() {
    if [ -f "$LOG_FILE" ]; then
        if [ "$1" = "-f" ]; then
            tail -f "$LOG_FILE"
        else
            tail -n 50 "$LOG_FILE"
        fi
    else
        warn "Log file not found: $LOG_FILE"
    fi
}

# Main script logic
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs "$2"
        ;;
    health)
        curl -f http://localhost:5003/health || echo "Health check failed"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|health}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the service"
        echo "  stop    - Stop the service" 
        echo "  restart - Restart the service"
        echo "  status  - Show service status"
        echo "  logs    - Show last 50 log lines (use 'logs -f' to follow)"
        echo "  health  - Run health check"
        exit 1
        ;;
esac