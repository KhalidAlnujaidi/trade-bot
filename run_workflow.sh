#!/bin/bash
set -euo pipefail

# Color codes for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Script information
SCRIPT_NAME=$(basename "$0")
VERSION="1.0.0"

# Default configuration
NEWS_URL="https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports"
VENV_DIR="${PWD}/venv"
REQUIREMENTS="requirements.txt"

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script's directory to ensure correct file paths
cd "$SCRIPT_DIR"

# Logging function
log() {
    local level=$1
    local message=$2
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "[${timestamp}] ${GREEN}INFO${NC}: ${message}"
            ;;
        "WARNING")
            echo -e "[${timestamp}] ${YELLOW}WARNING${NC}: ${message}" >&2
            ;;
        "ERROR")
            echo -e "[${timestamp}] ${RED}ERROR${NC}: ${message}" >&2
            ;;
    esac
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Setup virtual environment
setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log "INFO" "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
    
    # Activate virtual environment
    if [ -f "${VENV_DIR}/bin/activate" ]; then
        source "${VENV_DIR}/bin/activate"
    else
        log "ERROR" "Failed to activate virtual environment"
        return 1
    fi
    
    # Install requirements if they exist
    if [ -f "$REQUIREMENTS" ]; then
        log "INFO" "Installing Python dependencies..."
        pip install --upgrade pip
        pip install -r "$REQUIREMENTS"
    else
        log "WARNING" "${REQUIREMENTS} not found, skipping dependency installation"
    fi
}

# Display usage information
usage() {
    echo "Usage: ${SCRIPT_NAME} [OPTION]"
    echo "Run the stock market news scraping and analysis workflow."
    echo ""
    echo "Options:"
    echo "  -h, --help     Display this help message and exit"
    echo "  -v, --version  Display version information and exit"
    echo "  --url URL      Custom news URL (default: ${NEWS_URL})"
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            ;;
        -v|--version)
            echo "${SCRIPT_NAME} version ${VERSION}"
            exit 0
            ;;
        --url)
            NEWS_URL="$2"
            shift 2
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main function
main() {
    log "INFO" "Starting workflow..."
    
    # Check for Python
    if ! command_exists python3; then
        log "ERROR" "Python 3 is required but not installed"
        exit 1
    fi
    
    # Setup virtual environment
    if ! setup_venv; then
        log "ERROR" "Failed to setup virtual environment"
        exit 1
    fi
    
    # Step 1: Run the Selenium scraper
    log "INFO" "Starting news scraping process..."
    if ! python3 selenium_open_page.py "$NEWS_URL"; then
        log "ERROR" "The scraping script failed. Aborting workflow."
        exit 1
    fi
    log "INFO" "Scraping process completed."
    
    # Step 2: Run the analysis script
    log "INFO" "Starting analysis process..."
    if ! python3 analysis.py; then
        log "ERROR" "The analysis script failed."
        exit 1
    fi
    log "INFO" "Analysis process completed."
    
    log "INFO" "Workflow finished successfully."
}

# Run the main function
main "$@"

