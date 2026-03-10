# TechCrunch Reader - Robinhood Startup Fund News 📈

A modern Flask application that displays and analyzes TechCrunch articles about Robinhood's startup fund NYSE debut.

## 🎯 Overview

This application provides a clean interface for reading and exploring news articles about Robinhood's startup fund, with portfolio visualization and data analysis features.

## ✨ Features

- **Article Display** - Clean reading experience for TechCrunch articles
- **Portfolio Visualization** - Interactive charts using Chart.js
- **API Endpoints** - JSON data for programmatic access
- **Responsive Design** - Works on desktop and mobile devices
- **Data Export** - Export article data in various formats

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/none-ai/robinhood-startup.git
cd robinhood-startup

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Open your browser and visit:
```
http://localhost:5000
```

## 📋 Routes

| Route | Description |
|-------|-------------|
| `/` | Home page with article summary |
| `/article` | Full article content |
| `/api/data` | JSON API endpoint |
| `/portfolio` | Portfolio visualization |

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask 3.0.0
- **Frontend**: HTML5, CSS3, JavaScript
- **Visualization**: Chart.js
- **Database**: SQLite (optional)

## 📊 Example API Response

```json
{
  "title": "Robinhood's Startup Fund Debuts on NYSE",
  "summary": "Robinhood's new initiative...",
  "date": "2024-01-15",
  "portfolio_value": 50000000
}
```

## 📄 License

MIT License

---

Author: stlin256's openclaw
