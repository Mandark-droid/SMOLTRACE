#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# Ensure you have set the following environment variables:
# TESTPYPI_API_TOKEN: Your API token for TestPyPI
# (Optional) TWINE_USERNAME: Usually '__token__'

# --- Script Start ---
echo "Starting release test script..."

# --- Environment Setup ---
echo "Setting up Python environment and installing dependencies..."

# Ensure pip is up-to-date
python -m pip install --upgrade pip

python -m pip install ruff pytest build twine black isort

# Install project in editable mode with development dependencies
# This assumes the script is run from the project root directory
python -m pip install -e .[dev]

echo "Dependencies installed."

# --- Apply Formatting ---
echo "Applying code formatters..."
black .
isort .
ruff format .

# --- Formatting and Linting ---
echo "Running linters and formatters..."
ruff check .
black --check .
isort --check-only .
#pylint smoltrace

# --- Testing ---
echo "Running tests..."
pytest

# --- Building Package ---
echo "Building the package..."
python -m build

# --- Uploading to TestPyPI ---
echo "Attempting to upload to TestPyPI..."

# Check if TestPyPI token is set
if [ -z "$TESTPYPI_API_TOKEN" ]; then
  echo "Error: TESTPYPI_API_TOKEN environment variable is not set."
  echo "Please set it to your TestPyPI API token."
  exit 1
fi

# Set TWINE_USERNAME if not already set
if [ -z "$TWINE_USERNAME" ]; then
  export TWINE_USERNAME="__token__"
  echo "TWINE_USERNAME set to '__token__'."
fi

# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

echo "Package successfully uploaded to TestPyPI."
echo "Release test script finished."
