# Stock News Dashboard

A web application to browse and analyze stock news articles with sentiment analysis.

## Features

- Browse all stock news articles with pagination
- Search functionality to find specific articles
- View detailed article pages with full content
- Sentiment analysis visualization (Up/Down/Neutral)
- Confidence indicators for sentiment analysis
- Clean, responsive design using Bootstrap 5

## Prerequisites

- Python 3.8+
- SQLite3 (included with Python)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd trade-bot
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. Make sure you have the `stock_news.db` file in the project root directory.

2. Start the development server:
   ```bash
   python app.py
   ```

3. Open your web browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

## Production Deployment

For production deployment, it's recommended to use a production WSGI server like Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Project Structure

- `app.py` - Main application file with Flask routes
- `templates/` - HTML templates using Jinja2
  - `base.html` - Base template with common layout
  - `index.html` - Homepage with article list
  - `article.html` - Individual article page
- `requirements.txt` - Python dependencies
- `stock_news.db` - SQLite database with stock news articles

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
