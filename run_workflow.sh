#!/bin/bash

# This script automates the process of scraping and analyzing stock market news.

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script's directory to ensure correct file paths
cd "$SCRIPT_DIR"

# Define the URL for the news articles
NEWS_URL="https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports"

# Step 1: Run the Selenium scraper to get the latest news
echo "Starting news scraping process..."
python3 selenium_open_page.py "$NEWS_URL"

# Check if the scraper ran successfully
if [ $? -ne 0 ]; then
  echo "Error: The scraping script failed. Aborting workflow."
  exit 1
fi

echo "Scraping process completed."

# Step 2: Run the analysis script on the newly scraped articles
echo "Starting analysis process..."
python3 analysis.py

# Check if the analysis script ran successfully
if [ $? -ne 0 ]; then
  echo "Error: The analysis script failed."
  exit 1
fi

echo "Analysis process completed."

echo "Workflow finished successfully."
