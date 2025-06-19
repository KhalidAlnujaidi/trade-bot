import os
from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap
from flask_paginate import Pagination
from db_service import get_db_connection, fetch_articles, fetch_article_by_id

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['DATABASE'] = 'stock_news.db'

# Initialize Bootstrap with the app
bootstrap = Bootstrap(app)

# TODO: Add support for user authentication and role-based access control.

# All DB access is now handled via db_service.py for modularity and testability.
# See db_service.py for CRUD interface details and data shape comments.
# TODO: Add API endpoints for article creation and deletion.

@app.route('/')
def index() -> str:
    """
    Main page showing a list of stock news articles with pagination.
    Inputs: Query params 'search' (str, optional), 'page' (int, optional)
    Output: HTML page with paginated list of articles
    Each article: {id, title, url, publication_date, snippet, llm_evaluation, llm_confidence, llm_reasoning}
    """
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    conn = get_db_connection(app.config['DATABASE'])
    articles, total = fetch_articles(conn, search=search if search != '' else None, page=page, per_page=per_page)
    pagination = Pagination(
        page=page,
        per_page=per_page,
        total=total,
        search=search,
        record_name='articles',
        css_framework='bootstrap4'
    )
    conn.close()
    return render_template(
        'index.html',
        articles=articles,
        search=search,
        pagination=pagination,
        total=total
    )
# TODO: Add API for exporting articles as CSV or JSON.

@app.route('/article/<int:article_id>')
def article(article_id: int) -> str:
    """
    Display a single article in detail.
    Input: article_id (int)
    Output: HTML page for article detail, or 404 if not found
    Article shape: {id, title, url, publication_date, article_text, attachments_text, llm_evaluation, llm_confidence, llm_reasoning, ...}
    """
    conn = get_db_connection(app.config['DATABASE'])
    art = fetch_article_by_id(conn, article_id)
    conn.close()
    if art is None:
        return 'Article not found', 404
    return render_template('article.html', article=art)
# TODO: Add support for comments and related articles.

if __name__ == '__main__':
    app.run(debug=True)
