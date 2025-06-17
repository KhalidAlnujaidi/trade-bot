import os
import sqlite3
import json
from openai import OpenAI
from dotenv import load_dotenv

# --- CONFIGURATION ---
# Load environment variables from .env file
load_dotenv()
DB_PATH = '/Users/khalid/trade-bot/stock_news.db'
# TODO: The user should create a .env file and add their OPENAI_API_KEY
# Get the API key from environment variables
API_KEY = os.getenv("OPENAI_API_KEY")

# --- DATABASE FUNCTIONS ---

def get_db_connection():
    """
    Establishes a connection to the SQLite database.
    The connection is configured to return rows that behave like dictionaries.
    Returns:
        sqlite3.Connection: A database connection object.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

def get_unprocessed_articles(conn):
    """
    Fetches articles that have not yet been processed by the LLM.
    An article is considered unprocessed if its processing_status is 'new' or NULL.
    Args:
        conn (sqlite3.Connection): The database connection object.
    Returns:
        list: A list of row objects (dictionaries) for each unprocessed article.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, article_text FROM articles WHERE processing_status IS NULL OR processing_status = 'new' OR processing_status = 'pending'"
    )
    articles = cursor.fetchall()
    return articles

def update_article_analysis(conn, article_id, evaluation, reasoning, confidence):
    """
    Updates an article's record with the analysis results from the LLM.
    It also sets the processing_status to 'processed'.
    Args:
        conn (sqlite3.Connection): The database connection object.
        article_id (int): The ID of the article to update.
        evaluation (str): The evaluation from the LLM (e.g., 'Up', 'Down').
        reasoning (str): The reasoning text from the LLM.
        confidence (float): The confidence score from the LLM.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE articles
        SET
            llm_evaluation = ?,
            llm_reasoning = ?,
            llm_confidence = ?,
            processing_status = 'processed'
        WHERE id = ?
        """,
        (evaluation, reasoning, confidence, article_id)
    )
    conn.commit()
    print(f"Successfully updated article ID: {article_id}")

# --- AI ANALYSIS FUNCTION ---

def get_article_analysis(client, article_title, article_body):
    """
    Generates a prompt and sends it to the OpenAI API for analysis.
    Args:
        client (OpenAI): The OpenAI client instance.
        article_title (str): The title of the news article.
        article_body (str): The full text of the news article.
    Returns:
        dict: A dictionary containing the parsed JSON response from the LLM,
              or None if an error occurs.
    """
    # This prompt is adapted from the user's original script.
    prompt = f"""
You are a seasoned sell-side equity research analyst with deep knowledge of how news, macro events, and market psychology affect share prices in the short term (next 1-5 trading days).

TASK
Read the news item provided below and judge its **likely immediate impact** on the quoted company’s stock price.

INPUT
News article title: {article_title}
Full article text (verbatim):
<<<
{article_body}
>>>

OUTPUT – return **exactly** this JSON (no extra keys, no commentary outside the JSON block):

```json
{{
  "llm_evaluation": "<One of: Up | Down | Neutral>",
  "llm_reasoning": "<Concise rationale (80-120 words) citing the specific drivers in the article, any offsetting factors, and reference to broader market context when relevant.>",
  "llm_confidence": <Integer 0–10 where 0 = no expected price move and 10 = very high certainty & magnitude of move in the indicated direction>
}}
```
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}, # Ensure JSON output
        )
        response_content = response.choices[0].message.content
        # The response content is a JSON string, so we parse it.
        analysis_json = json.loads(response_content)
        return analysis_json
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from LLM response: {e}")
        print(f"Raw response: {response_content}")
        return None
    except Exception as e:
        print(f"An error occurred during OpenAI API call: {e}")
        return None

# --- MAIN EXECUTION ---

def main():
    """
    Main function to run the analysis pipeline.
    It connects to the DB, fetches unprocessed articles, analyzes them,
    and updates the database with the results.
    """
    if not API_KEY:
        print("FATAL: No OPENAI_API_KEY found in environment variables.")
        print("Please create a .env file in the root directory and add your key, e.g., OPENAI_API_KEY='sk-...' ")
        return

    client = OpenAI(api_key=API_KEY)
    conn = get_db_connection()

    try:
        articles_to_process = get_unprocessed_articles(conn)
        if not articles_to_process:
            print("No new articles to process.")
            return

        print(f"Found {len(articles_to_process)} articles to analyze.")

        for article in articles_to_process:
            print(f"\n--- Processing Article ID: {article['id']} ---")
            print(f"Title: {article['title']}")

            # Guard against empty article text
            if not article['article_text'] or not article['article_text'].strip():
                print("Article text is empty, skipping analysis.")
                update_article_analysis(conn, article['id'], 'Error', 'Article text was empty', 0.0)
                continue

            analysis_result = get_article_analysis(client, article['title'], article['article_text'])

            if analysis_result:
                # Basic validation of the returned JSON structure
                if all(k in analysis_result for k in ['llm_evaluation', 'llm_reasoning', 'llm_confidence']):
                    update_article_analysis(
                        conn,
                        article['id'],
                        analysis_result['llm_evaluation'],
                        analysis_result['llm_reasoning'],
                        float(analysis_result['llm_confidence'])
                    )
                else:
                    print("Error: LLM response did not contain all required keys.")
                    # Optionally, update DB with an error status
                    update_article_analysis(conn, article['id'], 'Error', f'Malformed LLM response: {analysis_result}', 0.0)
            else:
                print("Failed to get analysis from LLM. Skipping update for this article.")
                # Optionally, update DB with an error status
                update_article_analysis(conn, article['id'], 'Error', 'LLM API call failed', 0.0)

    except sqlite3.Error as e:
        print(f"A database error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == '__main__':
    main()
    # TODO: After running, check the 'articles' table in stock_news.db to see the new llm_* fields populated.
