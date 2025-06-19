# Stock News Dashboard

A web-based dashboard for visualizing stock news analysis data.

## Features

- Real-time statistics on news articles
- Sentiment analysis visualization
- Trend analysis over time
- Responsive design that works on desktop and mobile

## Prerequisites

- Python 3.7+
- pip (Python package manager)
- Node.js and npm (for frontend dependencies, though we're using CDN for now)

## Installation

1. Navigate to your project root directory:
   ```bash
   cd /path/to/trade-bot
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Dashboard

1. Start the FastAPI server:
   ```bash
   cd dashboard
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:8000
   ```

## Project Structure

```
dashboard/
├── app.py                 # FastAPI application
├── static/                # Static files (CSS, JS, images)
│   └── js/
│       └── dashboard.js  # Frontend JavaScript
├── templates/             # HTML templates
│   └── dashboard.html     # Main dashboard page
└── README.md             # This file
```

## API Endpoints

- `GET /` - Main dashboard page
- `GET /api/articles` - Get all articles with sentiment analysis
- `GET /api/articles/trend` - Get article trend data for the last 30 days

## Customization

You can customize the dashboard by modifying:

- `templates/dashboard.html` - For layout and structure
- `static/js/dashboard.js` - For frontend functionality and charts
- `app.py` - For backend API endpoints and data processing

## License

This project is open source and available under the MIT License.
