# TechCrunch Reader - Robinhood Startup Fund News

A simple Flask application displaying a TechCrunch article about Robinhood's startup fund NYSE debut.

## Features

- **Home Page** (`/`) - Overview of the latest article
- **Article Page** (`/article`) - Full article content
- **API Endpoint** (`/api/data`) - JSON data for programmatic access

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open your browser:
```
http://localhost:5000
```

## Routes

| Route | Description |
|-------|-------------|
| `/` | Home page with article summary |
| `/article` | Full article content |
| `/api/data` | JSON API endpoint |

## Tech Stack

- Python 3
- Flask 3.0.0
- Chart.js for portfolio visualization

作者: stlin256的openclaw
