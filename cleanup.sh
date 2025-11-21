#!/bin/bash

# cleanup.sh - Clean up cache files and temporary files from the project

echo "🧹 Cleaning up cache files and temporary files..."

# Function to safely remove files/directories
safe_remove() {
    if [ -e "$1" ]; then
        echo "  🗑️  Removing: $1"
        rm -rf "$1"
    fi
}

# Python cache files
echo "Cleaning Python cache files..."
find . -type d -name "__pycache__" -not -path "./dependency-analysis-service/venv/*" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -not -path "./dependency-analysis-service/venv/*" -delete 2>/dev/null || true
find . -name "*.pyo" -not -path "./dependency-analysis-service/venv/*" -delete 2>/dev/null || true
find . -name "*~" -delete 2>/dev/null || true

# macOS files
echo "Cleaning macOS files..."
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "._*" -delete 2>/dev/null || true

# Log files
echo "Cleaning log files..."
find . -name "*.log" -not -path "./dependency-analysis-service/venv/*" -delete 2>/dev/null || true

# Temporary files
echo "Cleaning temporary files..."
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.temp" -delete 2>/dev/null || true
safe_remove "./tmp"
safe_remove "./temp"

# IDE files
echo "Cleaning IDE files..."
safe_remove "./.vscode"
safe_remove "./.idea"
find . -name "*.swp" -delete 2>/dev/null || true
find . -name "*.swo" -delete 2>/dev/null || true

# Service files
echo "Cleaning service files..."
find . -name "*.pid" -delete 2>/dev/null || true
safe_remove "./temp_repos"
safe_remove "./gradle_analysis"

# Coverage files
echo "Cleaning coverage files..."
safe_remove "./.coverage"
safe_remove "./htmlcov"
safe_remove "./coverage"

echo "✅ Cleanup complete!"

# Show what would be ignored by git
echo ""
echo "📝 Files that are now properly ignored by git:"
git status --ignored --porcelain=v1 2>/dev/null | grep "^!!" | head -10 || echo "  (Run 'git status --ignored' to see ignored files)"