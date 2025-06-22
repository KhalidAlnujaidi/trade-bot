import os
import sqlite3
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv
from serpapi import GoogleSearch # Import the search library

# --- Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = 'stock_news.db'
OPENAI_MODEL = "gpt-4-turbo"
ALLOWED_EVALUATIONS = {"Bullish", "Bearish", "Neutral"}

# --- Client Initialization ---
# OpenAI Client
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    logging.error("No OPENAI_API_KEY found in .env file.")
    raise ValueError("OPENAI_API_KEY is not set.")
client = OpenAI(api_key=openai_api_key)

# SerpApi Client
serpapi_api_key = os.getenv("SERPAPI_API_KEY")
if not serpapi_api_key:
    logging.error("No SERPAPI_API_KEY found in .env file.")
    raise ValueError("SERPAPI_API_KEY is not set.")

# --- Database and Search Functions ---

def get_db_connection():
    """Establishes and returns a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def perform_web_search(query, num_results=3):
    """Performs a web search using SerpApi and returns top results."""
    logging.info(f"Performing web search for: '{query}'")
    try:
        params = {
            "q": query,
            "api_key": serpapi_api_key,
            "num": num_results
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        
        # Extract relevant organic results
        organic_results = results.get("organic_results", [])
        if not organic_results:
            logging.warning(f"No organic results found for query: '{query}'")
            return []
            
        return [
            {"title": r.get("title"), "snippet": r.get("snippet")}
            for r in organic_results
        ]
    except Exception as e:
        logging.error(f"Error during web search for '{query}': {e}")
        return [] # Return empty list on error to not halt the process

# The prompt function is now the advanced version
def build_advanced_prompt(article_title, article_text, company_name, search_results):
    """Builds an advanced prompt for the LLM, incorporating web search results."""
    formatted_search_results = "\n\n".join(
        [f"Source {i+1}: {res['title']}\n{res['snippet']}" for i, res in enumerate(search_results)]
    )
    # The new prompt structure goes here (as defined in the section above)
    return f"""
You are a Senior Equity Research Analyst at a major investment bank, tasked with providing a concise, actionable analysis of a news article. Your analysis must be grounded in the provided text and supplemented by the latest web search results.

**Company:** {company_name}
**News Article Title:** "{article_title}"
**Full Article Text:**
---
{article_text}
---
**Recent Web Search Results (for additional context):**
---
{formatted_search_results}
---
**Your Task:**
Based on all the information above, provide a structured financial assessment. Your entire response must be a single, valid JSON object.

**JSON Structure Requirements:**
1.  `evaluation` (String): Your overall assessment. Choose ONE: "Bullish", "Bearish", "Neutral".
2.  `timescale` (String): The expected timeframe for the impact. Choose ONE: "Intraday (1 day)", "Short-term (1-4 weeks)", "Medium-term (1-6 months)".
3.  `magnitude` (String): The potential magnitude of the stock price movement. Choose ONE: "Low (<2%)", "Medium (2-5%)", "High (>5%)".
4.  `reasoning` (Object): A structured rationale. This object must contain two keys:
    * `bullish_drivers` (Array of strings): List the key positive points from the news and search results.
    * `bearish_drivers` (Array of strings): List the key negative or offsetting points. If none, provide an empty array [].
5.  `confidence` (Integer): Your confidence in this entire assessment, from 0 (no certainty) to 10 (high certainty).
6.  `confidence_reasoning` (String): A brief justification for your confidence score, explaining what factors make you more or less certain.

**Example of a perfect response format:**
{{
  "evaluation": "Bullish",
  "timescale": "Short-term (1-4 weeks)",
  "magnitude": "Medium (2-5%)",
  "reasoning": {{
    "bullish_drivers": ["New product launch exceeded analyst expectations.", "Positive forward-looking guidance from CEO."],
    "bearish_drivers": ["Increased R&D spending could impact next quarter's margins."]
  }},
  "confidence": 8,
  "confidence_reasoning": "The CEO's direct quotes and specific sales figures provide a strong basis for a positive outlook, though broader market volatility prevents maximum confidence."
}}

Begin your analysis now.
"""

def update_article_analysis_advanced(conn, article_id, analysis_json):
    """Updates the article in the DB, storing the entire JSON analysis."""
    try:
        with conn:
            conn.execute(
                """
                UPDATE articles
                SET llm_evaluation = ?, 
                    llm_reasoning = ?, 
                    llm_confidence = ?, 
                    processing_status = 'processed',
                    llm_full_response = ?
                WHERE id = ?
                """,
                (
                    analysis_json.get("evaluation"),
                    json.dumps(analysis_json.get("reasoning")), # Store the reasoning object as a JSON string
                    analysis_json.get("confidence"),
                    json.dumps(analysis_json), # Store the full response
                    article_id,
                )
            )
        logging.info(f"Successfully updated article ID {article_id} with advanced analysis.")
    except sqlite3.Error as e:
        logging.error(f"Database error updating article ID {article_id}: {e}")

# This assumes your 'articles' table has a new column: llm_full_response TEXT
# You might need to run this SQL command once on your DB:
# ALTER TABLE articles ADD COLUMN llm_full_response TEXT;


def main():
    """Main function to fetch, search, analyze, and update articles."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, article_text, company_name FROM articles WHERE processing_status = 'pending'")
    # We now assume a 'company_name' column exists.
    pending_articles = cursor.fetchall()

    if not pending_articles:
        logging.info("No pending articles found.")
        conn.close()
        return

    logging.info(f"Found {len(pending_articles)} pending articles.")

    for row in pending_articles:
        article_id = row['id']
        title = row['title']
        company_name = row.get('company_name') # Get company name from the row

        if not company_name:
            logging.warning(f"Skipping article ID {article_id} due to missing company name.")
            continue
            
        logging.info(f"Processing article ID {article_id} for company: {company_name}")

        # Step 1: Perform web search
        search_query = f"{company_name} stock news"
        search_results = perform_web_search(search_query)

        # Step 2: Build the advanced prompt
        prompt = build_advanced_prompt(title, row['article_text'], company_name, search_results)

        # Step 3: Call the LLM
        try:
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            result_json = json.loads(content)

            # A simple validation could be to check for the top-level keys
            required_keys = {"evaluation", "timescale", "magnitude", "reasoning", "confidence", "confidence_reasoning"}
            if not required_keys.issubset(result_json.keys()):
                 logging.warning(f"Article ID {article_id}: Response missing required keys.")
                 continue

            # Step 4: Update the database
            update_article_analysis_advanced(conn, article_id, result_json)

        except Exception as e:
            logging.error(f"An unexpected error occurred for article ID {article_id}: {e}")

    conn.close()
    logging.info("Processing complete.")

if __name__ == "__main__":
    main()