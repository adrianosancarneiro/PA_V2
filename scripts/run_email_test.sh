#!/bin/bash

# This script ensures the email integration system is run with the correct dependencies

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Activate the virtual environment
source "$PROJECT_ROOT/.venv/bin/activate"

# Install required packages using UV if they're not already installed
echo "Checking and installing required packages with UV..."
cd "$PROJECT_ROOT"
uv sync

# Add src directory to PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

echo "Running email integration tests..."

# Run the setup script
echo "Setting up email authentication..."
python "$PROJECT_ROOT/tools/setup_email_auth.py"

# Run the test script
echo "Testing email integration..."
python "$PROJECT_ROOT/tests/test_email_integration.py"

# Update requirements in pyproject.toml
if [ ! -f "pyproject.toml" ]; then
    echo "Creating pyproject.toml file..."
    cat > pyproject.toml << EOL
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pa_v2"
version = "0.1.0"
description = "Personal Assistant V2"
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "google-api-python-client",
    "google-auth-httplib2",
    "google-auth-oauthlib",
    "msal",
    "requests",
]

[tool.uv]
exclude = []
EOL
else
    echo "pyproject.toml already exists, not modifying it."
fi

# Run the test script within the virtual environment
echo "Running the email integration test..."
python test_email_integration.py
