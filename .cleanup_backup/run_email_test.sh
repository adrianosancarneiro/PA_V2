#!/bin/bash

# This script ensures the email integration system is run with the correct dependencies

# Activate the virtual environment
source .venv/bin/activate

# Install required packages if they're not already installed
echo "Checking and installing required packages..."
uv pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib msal requests

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
