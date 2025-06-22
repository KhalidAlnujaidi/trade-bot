#!/bin/bash

# Setup and run the full workflow: database setup + workflow
# Usage: ./setup_and_run.sh [workflow options]

set -e

# Step 1: Setup the database
echo "[1/2] Setting up the database..."
python3 database_setup.py

# Step 2: Run the workflow with web search enabled by default
echo "[2/2] Running the workflow with USE_WEB_SEARCH=1 (web search enabled by default)..."
USE_WEB_SEARCH=1 ./run_workflow.sh "$@" 