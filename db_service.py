"""
db_service.py

Encapsulates all CRUD operations for the stock_news.db database so that business logic can switch between local, on-prem, or cloud backends without changes. All functions are documented with input/output types and data shapes.

// TODO: Add support for cloud DB backends. See issue #db-cloud-support
"""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = 'stock_news.db'

# --- CONNECTION MANAGEMENT ---
def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Establishes and returns a database connection.
    Args:
        db_path (str): Path to the SQLite database file.
    Returns:
        sqlite3.Connection: Connection object to the SQLite database.
    Side effects:
        Opens a connection to the database file.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# --- CRUD OPERATIONS ---
def fetch_articles(
    conn: sqlite3.Connection,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 10
) -> Tuple[List[sqlite3.Row], int]:
    """
    Retrieves paginated articles with optional search.
    Args:
        conn (sqlite3.Connection): DB connection.
        search (str, optional): Search term for title/content.
        page (int): Page number.
        per_page (int): Items per page.
    Returns:
        Tuple[List[sqlite3.Row], int]: (list of articles, total count)
    Output shape:
        Each row: {id, title, url, publication_date, snippet, llm_evaluation, llm_confidence, llm_reasoning}
    """
    offset = (page - 1) * per_page
    query = """
        SELECT id, title, url, publication_date, 
               substr(article_text, 1, 200) || '...' as snippet,
               llm_evaluation, llm_confidence, llm_reasoning
        FROM articles
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (title LIKE ? OR article_text LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])
    count_query = f"SELECT COUNT(*) as count FROM ({query.replace('SELECT id, title, url, publication_date, substr(article_text, 1, 200) || \'...\' as snippet, llm_evaluation, llm_confidence, llm_reasoning', 'SELECT id')})"
    total = conn.execute(count_query, params).fetchone()['count']
    query += " ORDER BY publication_date DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    articles = conn.execute(query, params).fetchall()
    return articles, total


def fetch_article_by_id(conn: sqlite3.Connection, article_id: int) -> Optional[sqlite3.Row]:
    """
    Fetches a single article by its ID.
    Args:
        conn (sqlite3.Connection): DB connection.
        article_id (int): Article ID.
    Returns:
        Optional[sqlite3.Row]: Row dict or None if not found.
    Output shape:
        {id, title, url, publication_date, article_text, attachments_text, llm_evaluation, llm_confidence, llm_reasoning, ...}
    """
    return conn.execute('SELECT * FROM articles WHERE id = ?', (article_id,)).fetchone()


def fetch_unprocessed_articles(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    """
    Fetches all articles not processed by the LLM.
    Args:
        conn (sqlite3.Connection): DB connection.
    Returns:
        List[sqlite3.Row]: List of row dicts.
    Output shape:
        [{id, title, article_text, ...}, ...]
    """
    return conn.execute(
        "SELECT id, title, article_text FROM articles WHERE processing_status IS NULL OR processing_status = 'new' OR processing_status = 'pending'"
    ).fetchall()


def update_article_analysis(
    conn: sqlite3.Connection,
    article_id: int,
    evaluation: str,
    reasoning: str,
    confidence: float
) -> None:
    """
    Updates an article with LLM analysis results.
    Args:
        conn (sqlite3.Connection): DB connection.
        article_id (int): Article ID.
        evaluation (str): LLM evaluation (e.g., 'Up', 'Down', 'Neutral').
        reasoning (str): LLM rationale.
        confidence (float): LLM confidence score.
    Side effects:
        Updates DB row for the article.
    """
    conn.execute(
        """
        UPDATE articles
        SET llm_evaluation = ?, llm_reasoning = ?, llm_confidence = ?, processing_status = 'processed'
        WHERE id = ?
        """,
        (evaluation, reasoning, confidence, article_id)
    )
    conn.commit()

# TODO: Add CRUD for article creation/deletion and for attachments
# TODO: Add error handling wrappers for all DB operations
# TODO: Add unit tests for all service functions
