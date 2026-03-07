from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# Sample article data
article = {
    "title": "Robinhood's startup fund stumbles in NYSE debut",
    "source": "TechCrunch",
    "date": "2026-03-07",
    "summary": "Robinhood's much-anticipated startup fund made its NYSE debut today, but the launch was met with significant challenges. The fund, which aims to provide retail investors access to startup equity, saw its shares trade well below expectations.",
    "content": """
    Robinhood's entry into the startup investment space faced an unexpected stumbling block on its first day of trading on the New York Stock Exchange. The cryptocurrency and stock trading platform's new startup fund opened at $38 per share, significantly below the initial target of $45.

    Market analysts pointed to several factors contributing to the underwhelming debut:
    - Concerns about Robinhood's regulatory challenges
    - Skepticism about the fund's fee structure
    - Broader market volatility affecting tech stocks

    "This is a rough start for Robinhood's venture into startup investments," said Sarah Chen, a fintech analyst at Morgan Stanley. "The company will need to demonstrate strong performance to win back investor confidence."

    The fund, which allows retail investors to buy shares in private startups, represents Robinhood's expansion beyond its core trading platform. However, the rocky debut raises questions about the timing of this move.

    Robinhood CEO Vlad Tenev remained optimistic, stating, "We believe in the long-term potential of democratizing access to startup investments. Today's market reaction is just noise in the short term."

    The stock closed at $35.50, down 6.5% from the opening price.
    """
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ article.title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #1a1a1a;
            font-size: 28px;
        }
        .meta {
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
        }
        .summary {
            background: #e8f4f8;
            padding: 15px;
            border-left: 4px solid #00a0dc;
            margin: 20px 0;
        }
        .content {
            line-height: 1.8;
            white-space: pre-line;
        }
        nav {
            margin-bottom: 20px;
        }
        nav a {
            margin-right: 15px;
            color: #00a0dc;
            text-decoration: none;
        }
        nav a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <nav>
            <a href="/">Home</a>
            <a href="/article">Article</a>
            <a href="/api/data">API</a>
        </nav>
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

HOME_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h1>Welcome to TechCrunch Reader</h1>
    <p>Stay updated with the latest tech news.</p>
    <div class="summary">
        <h3>Latest Article:</h3>
        <h4>{{ article.title }}</h4>
        <p>{{ article.summary }}</p>
        <a href="/article">Read more →</a>
    </div>
{% endblock %}
"""

ARTICLE_TEMPLATE = """
{% extends "base" %}
{% block content %}
    <h1>{{ article.title }}</h1>
    <div class="meta">
        <span>Source: {{ article.source }}</span> |
        <span>Date: {{ article.date }}</span>
    </div>
    <div class="summary">
        <strong>Summary:</strong> {{ article.summary }}
    </div>
    <div class="content">{{ article.content }}</div>
{% endblock %}
"""


@app.route('/')
def home():
    """Home page route"""
    return render_template_string(HTML_TEMPLATE.replace('{% block content %}{% endblock %}', HOME_TEMPLATE), article=article)


@app.route('/article')
def article_page():
    """Article detail page route"""
    return render_template_string(HTML_TEMPLATE.replace('{% block content %}{% endblock %}', ARTICLE_TEMPLATE), article=article)


@app.route('/api/data')
def api_data():
    """API route returning article as JSON"""
    return jsonify(article)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
