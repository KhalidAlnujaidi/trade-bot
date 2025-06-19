from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import sqlite3
from datetime import datetime, timedelta
import os

app = FastAPI()

# Set up paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "stock_news.db")

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render the main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/articles")
async def get_articles():
    """API endpoint to fetch all articles with their evaluations."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get articles with their evaluations
    cursor.execute("""
        SELECT id, title, url, publication_date, 
               llm_evaluation, llm_confidence, llm_reasoning
        FROM articles
        ORDER BY publication_date DESC
    """)
    
    articles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Calculate some statistics
    total_articles = len(articles)
    positive_articles = sum(1 for a in articles if a.get('llm_evaluation') == 'positive')
    negative_articles = sum(1 for a in articles if a.get('llm_evaluation') == 'negative')
    neutral_articles = total_articles - positive_articles - negative_articles
    
    # Calculate confidence distribution
    confidence_scores = [a.get('llm_confidence', 0) for a in articles if a.get('llm_confidence') is not None]
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
    
    return {
        "articles": articles,
        "stats": {
            "total_articles": total_articles,
            "positive_articles": positive_articles,
            "negative_articles": negative_articles,
            "neutral_articles": neutral_articles,
            "avg_confidence": round(avg_confidence * 100, 2)  # Convert to percentage
        },
        "last_updated": datetime.now().isoformat()
    }

@app.get("/api/articles/trend")
async def get_article_trend():
    """API endpoint to get article count trend over time."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get last 30 days of data
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    cursor.execute("""
        SELECT date(publication_date) as date, 
               COUNT(*) as total,
               SUM(CASE WHEN llm_evaluation = 'positive' THEN 1 ELSE 0 END) as positive,
               SUM(CASE WHEN llm_evaluation = 'negative' THEN 1 ELSE 0 END) as negative
        FROM articles
        WHERE date(publication_date) >= ?
        GROUP BY date(publication_date)
        ORDER BY date ASC
        """, (thirty_days_ago,))
    
    trend_data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {"trend_data": trend_data}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
