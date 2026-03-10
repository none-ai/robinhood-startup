"""
Robinhood-style Investment Platform
A modern stock trading simulation platform with authentication,
portfolio tracking, real-time price simulation, and transaction history.
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, g
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json
import random
import time
import uuid
import logging
from datetime import datetime, timedelta
from functools import wraps
import yfinance as yf

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'robinhood-clone-secret-key-2026'

# Request ID middleware
@app.before_request
def before_request():
    g.request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{g.request_id}] {request.method} {request.path}")

@app.after_request
def after_request(response):
    logger.info(f"[{g.request_id}] Status: {response.status_code}")
    response.headers['X-Request-ID'] = g.request_id
    return response

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'request_id': g.request_id}), 200

# Error handlers
@app.errorhandler(404)
def not_found(e):
    logger.warning(f"404 Not Found: {request.path}")
    return jsonify({'error': 'Not Found', 'message': 'Resource not found'}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"500 Internal Error: {e}")
    return jsonify({'error': 'Internal Server Error', 'message': 'Something went wrong'}), 500

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# In-memory data storage (in production, use a database)
users_db = {}
portfolio_db = {}
transactions_db = {}
watchlist_db = {}  # User watchlists: {user_id: [symbol1, symbol2, ...]}

# Stock price simulation data - extended with more stocks
STOCKS = {
    'AAPL': {'name': 'Apple Inc.', 'base_price': 185.50, 'sector': 'Technology'},
    'GOOGL': {'name': 'Alphabet Inc.', 'base_price': 141.80, 'sector': 'Technology'},
    'MSFT': {'name': 'Microsoft Corp.', 'base_price': 378.90, 'sector': 'Technology'},
    'AMZN': {'name': 'Amazon.com Inc.', 'base_price': 178.25, 'sector': 'Consumer'},
    'TSLA': {'name': 'Tesla Inc.', 'base_price': 248.50, 'sector': 'Automotive'},
    'NVDA': {'name': 'NVIDIA Corp.', 'base_price': 495.20, 'sector': 'Technology'},
    'META': {'name': 'Meta Platforms', 'base_price': 505.75, 'sector': 'Technology'},
    'JPM': {'name': 'JPMorgan Chase', 'base_price': 198.40, 'sector': 'Finance'},
    'V': {'name': 'Visa Inc.', 'base_price': 280.15, 'sector': 'Finance'},
    'WMT': {'name': 'Walmart Inc.', 'base_price': 165.30, 'sector': 'Retail'},
    'DIS': {'name': 'Walt Disney Co.', 'base_price': 112.50, 'sector': 'Entertainment'},
    'NFLX': {'name': 'Netflix Inc.', 'base_price': 485.30, 'sector': 'Entertainment'},
    'PYPL': {'name': 'PayPal Holdings', 'base_price': 62.15, 'sector': 'Finance'},
    'INTC': {'name': 'Intel Corp.', 'base_price': 43.20, 'sector': 'Technology'},
    'AMD': {'name': 'AMD Inc.', 'base_price': 145.80, 'sector': 'Technology'},
}

# Current stock prices (will be updated with real data)
current_prices = {symbol: data['base_price'] for symbol, data in STOCKS.items()}
price_changes = {symbol: 0.0 for symbol in STOCKS}


def fetch_real_time_prices():
    """Fetch real-time stock prices using yfinance"""
    global current_prices, price_changes, STOCKS

    symbols = list(STOCKS.keys())
    try:
        # Fetch data for all symbols at once
        tickers = yf.Tickers(' '.join(symbols))
        new_prices = {}

        for symbol in symbols:
            try:
                ticker = tickers.tickers[symbol]
                info = ticker.fast_info

                if hasattr(info, 'last_price') and info.last_price:
                    new_prices[symbol] = info.last_price
                elif hasattr(info, 'previous_close') and info.previous_close:
                    new_prices[symbol] = info.previous_close
                else:
                    # Fallback to base price if real price unavailable
                    new_prices[symbol] = STOCKS[symbol]['base_price']
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                new_prices[symbol] = STOCKS[symbol]['base_price']

        # Calculate price changes
        for symbol in new_prices:
            if symbol in current_prices and current_prices[symbol] > 0:
                change = ((new_prices[symbol] - current_prices[symbol]) / current_prices[symbol]) * 100
                price_changes[symbol] = round(change, 2)
            else:
                price_changes[symbol] = 0.0

        current_prices = new_prices

    except Exception as e:
        print(f"Error fetching real-time prices: {e}")
        # Fallback to simulated prices
        simulate_price_change()


def fetch_stock_history(symbol, period='1mo'):
    """Fetch historical stock data for charts"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            return None

        # Format data for Chart.js
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        closes = hist['Close'].tolist()
        volumes = hist['Volume'].tolist()

        return {
            'dates': dates,
            'closes': [round(c, 2) for c in closes],
            'volumes': volumes,
            'high': round(hist['High'].max(), 2),
            'low': round(hist['Low'].min(), 2),
            'open': round(hist['Open'].iloc[0], 2),
            'current': round(hist['Close'].iloc[-1], 2)
        }
    except Exception as e:
        print(f"Error fetching history for {symbol}: {e}")
        return None


def search_stocks(query):
    """Search for stocks by symbol or company name"""
    results = []

    # Expand search with more stocks
    search_stocks_db = {
        'AAPL': 'Apple Inc.',
        'GOOGL': 'Alphabet Inc.',
        'MSFT': 'Microsoft Corporation',
        'AMZN': 'Amazon.com Inc.',
        'TSLA': 'Tesla Inc.',
        'NVDA': 'NVIDIA Corporation',
        'META': 'Meta Platforms Inc.',
        'JPM': 'JPMorgan Chase & Co.',
        'V': 'Visa Inc.',
        'WMT': 'Walmart Inc.',
        'DIS': 'The Walt Disney Company',
        'NFLX': 'Netflix Inc.',
        'PYPL': 'PayPal Holdings Inc.',
        'INTC': 'Intel Corporation',
        'AMD': 'Advanced Micro Devices',
        'BA': 'Boeing Company',
        'GS': 'Goldman Sachs',
        'IBM': 'IBM Corporation',
        'ORCL': 'Oracle Corporation',
        'CRM': 'Salesforce Inc.',
        'ADBE': 'Adobe Inc.',
        'CSCO': 'Cisco Systems',
        'PEP': 'PepsiCo Inc.',
        'KO': 'Coca-Cola Company',
        'MCD': 'McDonalds Corp.',
        'SBUX': 'Starbucks Corp.',
        'NKE': 'Nike Inc.',
        'HD': 'Home Depot Inc.',
        'BAC': 'Bank of America',
    }

    query_lower = query.lower()
    for symbol, name in search_stocks_db.items():
        if query_lower in symbol.lower() or query_lower in name.lower():
            price = current_prices.get(symbol, 0)
            results.append({
                'symbol': symbol,
                'name': name,
                'price': round(price, 2) if price else 0,
                'change': price_changes.get(symbol, 0)
            })

    return results


def simulate_price_change():
    """Simulate real-time price changes (fallback)"""
    global current_prices, price_changes
    for symbol in current_prices:
        change_percent = random.uniform(-0.5, 0.5)
        old_price = current_prices[symbol]
        current_prices[symbol] *= (1 + change_percent / 100)
        current_prices[symbol] = round(current_prices[symbol], 2)
        price_changes[symbol] = round(((current_prices[symbol] - old_price) / old_price) * 100, 2)


class User(UserMixin):
    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.cash_balance = 10000.00  # Starting balance
        self.created_at = datetime.now().isoformat()


@login_manager.user_loader
def load_user(user_id):
    return users_db.get(user_id)


# HTML Templates
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}OpenStock - Investment Platform{% endblock %}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #fff;
        }
        .navbar {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .logo {
            font-size: 1.5rem;
            font-weight: 700;
            color: #00d4aa;
            text-decoration: none;
        }
        .nav-links {
            display: flex;
            gap: 1.5rem;
            align-items: center;
        }
        .nav-links a {
            color: rgba(255,255,255,0.8);
            text-decoration: none;
            font-weight: 500;
            transition: color 0.3s;
        }
        .nav-links a:hover {
            color: #00d4aa;
        }
        .balance {
            background: rgba(0,212,170,0.1);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            color: #00d4aa;
            font-weight: 600;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 1.5rem;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        .card-title {
            font-size: 1.25rem;
            font-weight: 600;
        }
        .btn {
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary {
            background: linear-gradient(135deg, #00d4aa, #00a884);
            color: #1a1a2e;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,212,170,0.4);
        }
        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #fff;
        }
        .btn-secondary:hover {
            background: rgba(255,255,255,0.2);
        }
        .btn-danger {
            background: #ff4757;
            color: #fff;
        }
        .stock-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1rem;
        }
        .stock-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 1.25rem;
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s;
            cursor: pointer;
        }
        .stock-card:hover {
            transform: translateY(-4px);
            border-color: #00d4aa;
        }
        .stock-symbol {
            font-size: 1.25rem;
            font-weight: 700;
            color: #00d4aa;
        }
        .stock-name {
            color: rgba(255,255,255,0.6);
            font-size: 0.875rem;
            margin: 0.25rem 0;
        }
        .stock-price {
            font-size: 1.5rem;
            font-weight: 700;
            margin: 0.5rem 0;
        }
        .stock-change {
            font-size: 0.875rem;
            font-weight: 600;
        }
        .positive { color: #00d4aa; }
        .negative { color: #ff4757; }
        .form-group {
            margin-bottom: 1.5rem;
        }
        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
        }
        .form-group input {
            width: 100%;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.05);
            color: #fff;
            font-size: 1rem;
        }
        .form-group input:focus {
            outline: none;
            border-color: #00d4aa;
        }
        .auth-container {
            max-width: 400px;
            margin: 4rem auto;
        }
        .auth-card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 2rem;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .flash-messages {
            margin-bottom: 1rem;
        }
        .flash {
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }
        .flash-success { background: rgba(0,212,170,0.2); color: #00d4aa; }
        .flash-error { background: rgba(255,71,87,0.2); color: #ff4757; }
        .table {
            width: 100%;
            border-collapse: collapse;
        }
        .table th, .table td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .table th {
            color: rgba(255,255,255,0.6);
            font-weight: 500;
        }
        .portfolio-summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .summary-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
        }
        .summary-label {
            color: rgba(255,255,255,0.6);
            font-size: 0.875rem;
            margin-bottom: 0.5rem;
        }
        .summary-value {
            font-size: 1.5rem;
            font-weight: 700;
        }
        .price-updating {
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .tabs {
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        .tab {
            padding: 0.75rem 1.5rem;
            background: rgba(255,255,255,0.05);
            border: none;
            border-radius: 8px;
            color: #fff;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s;
        }
        .tab.active {
            background: #00d4aa;
            color: #1a1a2e;
        }
        .chart-container {
            height: 300px;
            margin-top: 1rem;
        }
        .search-container {
            position: relative;
            margin-bottom: 2rem;
        }
        .search-input {
            width: 100%;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.05);
            color: #fff;
            font-size: 1rem;
        }
        .search-input:focus {
            outline: none;
            border-color: #00d4aa;
        }
        .search-results {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: rgba(26, 26, 46, 0.98);
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.1);
            max-height: 400px;
            overflow-y: auto;
            z-index: 100;
            display: none;
        }
        .search-results.show {
            display: block;
        }
        .search-result-item {
            padding: 1rem 1.5rem;
            cursor: pointer;
            transition: background 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .search-result-item:hover {
            background: rgba(0,212,170,0.1);
        }
        .search-result-symbol {
            font-weight: 700;
            color: #00d4aa;
        }
        .search-result-name {
            color: rgba(255,255,255,0.6);
            font-size: 0.875rem;
        }
        .search-result-price {
            text-align: right;
        }
        .stock-detail-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 2rem;
        }
        .stock-detail-info h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        .stock-detail-price {
            font-size: 3rem;
            font-weight: 700;
        }
        .stock-detail-change {
            font-size: 1.25rem;
            font-weight: 600;
            margin-top: 0.5rem;
        }
        .stock-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
        }
        .stat-label {
            color: rgba(255,255,255,0.6);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .stat-value {
            font-size: 1.25rem;
            font-weight: 700;
            margin-top: 0.25rem;
        }
        .time-range-selector {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }
        .time-range-btn {
            padding: 0.5rem 1rem;
            background: rgba(255,255,255,0.05);
            border: none;
            border-radius: 6px;
            color: rgba(255,255,255,0.6);
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s;
        }
        .time-range-btn.active {
            background: #00d4aa;
            color: #1a1a2e;
        }
        .buy-sell-form {
            display: flex;
            gap: 1rem;
            align-items: flex-end;
        }
        .buy-sell-form .form-group {
            margin-bottom: 0;
            flex: 1;
        }
        .loading-spinner {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #00d4aa;
            animation: spin 1s ease-in-out infinite;
            margin-right: 0.5rem;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <a href="/" class="logo">📈 OpenStock</a>
        {% if current_user.is_authenticated %}
        <div class="nav-links">
            <a href="/">Market</a>
            <a href="/portfolio">Portfolio</a>
            <a href="/transactions">History</a>
            <span class="balance">${{ "%.2f"|format(current_user.cash_balance) }}</span>
            <a href="/logout" class="btn btn-secondary">Logout</a>
        </div>
        {% else %}
        <div class="nav-links">
            <a href="/login">Login</a>
            <a href="/register" class="btn btn-primary">Sign Up</a>
        </div>
        {% endif %}
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="flash-messages">
                    {% for category, message in messages %}
                        <div class="flash flash-{{ category }}">{{ message }}</div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
    <script>
        // Auto-refresh prices every 10 seconds
        {% if request.endpoint == 'index' or request.endpoint == 'portfolio' %}
        setInterval(() => {
            fetch('/api/prices')
                .then(res => res.json())
                .then(data => {
                    document.querySelectorAll('.stock-price').forEach(el => {
                        const symbol = el.dataset.symbol;
                        if (data.prices && data.prices[symbol]) {
                            el.textContent = '$' + data.prices[symbol].toFixed(2);
                        }
                    });
                    document.querySelectorAll('.stock-change-display').forEach(el => {
                        const symbol = el.dataset.symbol;
                        if (data.changes && data.changes[symbol] !== undefined) {
                            const change = data.changes[symbol];
                            el.textContent = (change >= 0 ? '▲' : '▼') + ' ' + Math.abs(change).toFixed(2) + '%';
                            el.className = 'stock-change stock-change-display ' + (change >= 0 ? 'positive' : 'negative');
                        }
                    });
                });
        }, 10000);
        {% endif %}

        // Search functionality
        const searchInput = document.getElementById('search-input');
        const searchResults = document.getElementById('search-results');

        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                const query = e.target.value.trim();

                if (query.length < 1) {
                    searchResults.classList.remove('show');
                    return;
                }

                searchTimeout = setTimeout(() => {
                    fetch(`/api/search?q=${encodeURIComponent(query)}`)
                        .then(res => res.json())
                        .then(data => {
                            if (data.results && data.results.length > 0) {
                                searchResults.innerHTML = data.results.map(r => `
                                    <a href="/stock/${r.symbol}" class="search-result-item">
                                        <div>
                                            <div class="search-result-symbol">${r.symbol}</div>
                                            <div class="search-result-name">${r.name}</div>
                                        </div>
                                        <div class="search-result-price">
                                            <div>$${r.price.toFixed(2)}</div>
                                            <div class="${r.change >= 0 ? 'positive' : 'negative'}" style="font-size: 0.875rem;">
                                                ${r.change >= 0 ? '▲' : '▼'} ${Math.abs(r.change).toFixed(2)}%
                                            </div>
                                        </div>
                                    </a>
                                `).join('');
                                searchResults.classList.add('show');
                            } else {
                                searchResults.innerHTML = '<div class="search-result-item">No results found</div>';
                                searchResults.classList.add('show');
                            }
                        });
                }, 300);
            });

            document.addEventListener('click', (e) => {
                if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                    searchResults.classList.remove('show');
                }
            });
        }
    </script>
</body>
</html>
"""

LOGIN_TEMPLATE = """
{% extends "base" %}
{% block title %}Login - OpenStock{% endblock %}
{% block content %}
<div class="auth-container">
    <div class="auth-card">
        <h2 style="text-align: center; margin-bottom: 2rem;">Welcome Back</h2>
        <form method="POST">
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="email" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary" style="width: 100%;">Login</button>
        </form>
        <p style="text-align: center; margin-top: 1.5rem; color: rgba(255,255,255,0.6);">
            Don't have an account? <a href="/register" style="color: #00d4aa;">Sign up</a>
        </p>
    </div>
</div>
{% endblock %}
"""

REGISTER_TEMPLATE = """
{% extends "base" %}
{% block title %}Register - OpenStock{% endblock %}
{% block content %}
<div class="auth-container">
    <div class="auth-card">
        <h2 style="text-align: center; margin-bottom: 2rem;">Create Account</h2>
        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="email" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary" style="width: 100%;">Create Account</button>
        </form>
        <p style="text-align: center; margin-top: 1.5rem; color: rgba(255,255,255,0.6);">
            Already have an account? <a href="/login" style="color: #00d4aa;">Login</a>
        </p>
    </div>
</div>
{% endblock %}
"""

INDEX_TEMPLATE = """
{% extends "base" %}
{% block title %}Market - OpenStock{% endblock %}
{% block content %}
<div class="card">
    <div class="card-header">
        <h2 class="card-title">Stock Market</h2>
        <div style="display: flex; align-items: center; gap: 1rem;">
            <span class="loading-spinner"></span>
            <span class="price-updating" style="color: rgba(255,255,255,0.6);">Live Prices</span>
        </div>
    </div>
    <div class="search-container">
        <input type="text" id="search-input" class="search-input" placeholder="Search stocks by symbol or name...">
        <div id="search-results" class="search-results"></div>
    </div>
    <div class="stock-grid">
        {% for symbol, data in stocks.items() %}
        <a href="/stock/{{ symbol }}" class="stock-card" style="text-decoration: none; color: inherit; display: block;">
            <div class="stock-symbol">{{ symbol }}</div>
            <div class="stock-name">{{ data.name }}</div>
            <div class="stock-price" data-symbol="{{ symbol }}">${{ "%.2f"|format(prices[symbol]) }}</div>
            <div class="stock-change stock-change-display {{ 'positive' if changes[symbol] >= 0 else 'negative' }}" data-symbol="{{ symbol }}">
                {{ '▲' if changes[symbol] >= 0 else '▼' }} {{ "%.2f"|format(changes[symbol]|abs) }}%
            </div>
            {% if current_user.is_authenticated %}
            <div style="margin-top: 1rem; display: flex; gap: 0.5rem;" onclick="event.stopPropagation();">
                <form action="/buy" method="POST" style="flex: 1;">
                    <input type="hidden" name="symbol" value="{{ symbol }}">
                    <input type="hidden" name="price" value="{{ prices[symbol] }}">
                    <input type="number" name="shares" min="1" value="1" style="width: 60px; padding: 0.5rem; border-radius: 4px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff;">
                    <button type="submit" class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 0.875rem;">Buy</button>
                </form>
            </div>
            {% endif %}
        </a>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

PORTFOLIO_TEMPLATE = """
{% extends "base" %}
{% block title %}Portfolio - OpenStock{% endblock %}
{% block content %}
<div class="portfolio-summary">
    <div class="summary-card">
        <div class="summary-label">Total Portfolio Value</div>
        <div class="summary-value" style="color: #00d4aa;">${{ "%.2f"|format(total_value) }}</div>
    </div>
    <div class="summary-card">
        <div class="summary-label">Cash Balance</div>
        <div class="summary-value">${{ "%.2f"|format(current_user.cash_balance) }}</div>
    </div>
    <div class="summary-card">
        <div class="summary-label">Invested Amount</div>
        <div class="summary-value">${{ "%.2f"|format(invested) }}</div>
    </div>
    <div class="summary-card">
        <div class="summary-label">Total Return</div>
        <div class="summary-value {{ 'positive' if total_return >= 0 else 'negative' }}">
            {{ "+" if total_return >= 0 else "" }}{{ "%.2f"|format(total_return) }}%
        </div>
    </div>
</div>

<div class="tabs">
    <button class="tab active" onclick="showTab('holdings')">Holdings</button>
    <button class="tab" onclick="showTab('chart')">Analytics</button>
</div>

<div id="holdings-tab">
    {% if portfolio %}
    <div class="card">
        <div class="card-header">
            <h2 class="card-title">Your Holdings</h2>
        </div>
        <table class="table">
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Shares</th>
                    <th>Avg Cost</th>
                    <th>Current Price</th>
                    <th>Value</th>
                    <th>Return</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {% for symbol, holding in portfolio.items() %}
                <tr>
                    <td><a href="/stock/{{ symbol }}" style="color: #00d4aa; text-decoration: none;"><strong>{{ symbol }}</strong></a></td>
                    <td>{{ holding.shares }}</td>
                    <td>${{ "%.2f"|format(holding.avg_cost) }}</td>
                    <td>${{ "%.2f"|format(prices[symbol]) }}</td>
                    <td>${{ "%.2f"|format(holding.shares * prices[symbol]) }}</td>
                    <td class="{{ 'positive' if (prices[symbol] - holding.avg_cost) >= 0 else 'negative' }}">
                        {{ "+" if (prices[symbol] - holding.avg_cost) >= 0 else "" }}{{ "%.2f"|format(((prices[symbol] - holding.avg_cost) / holding.avg_cost) * 100) }}%
                    </td>
                    <td>
                        <form action="/sell" method="POST" style="display: inline;">
                            <input type="hidden" name="symbol" value="{{ symbol }}">
                            <input type="hidden" name="price" value="{{ prices[symbol] }}">
                            <input type="number" name="shares" min="1" max="{{ holding.shares }}" value="1" style="width: 60px; padding: 0.5rem; border-radius: 4px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff;">
                            <button type="submit" class="btn btn-danger" style="padding: 0.5rem 1rem; font-size: 0.875rem;">Sell</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <div class="card" style="text-align: center; padding: 3rem;">
        <h3 style="margin-bottom: 1rem;">No Holdings Yet</h3>
        <p style="color: rgba(255,255,255,0.6); margin-bottom: 1.5rem;">Start investing by buying your first stock</p>
        <a href="/" class="btn btn-primary">Browse Market</a>
    </div>
    {% endif %}
</div>

<div id="chart-tab" style="display: none;">
    <div class="card">
        <div class="card-header">
            <h2 class="card-title">Portfolio Allocation</h2>
        </div>
        <div class="chart-container">
            <canvas id="portfolioChart"></canvas>
        </div>
    </div>
</div>

<script>
    function showTab(tabName) {
        document.getElementById('holdings-tab').style.display = tabName === 'holdings' ? 'block' : 'none';
        document.getElementById('chart-tab').style.display = tabName === 'chart' ? 'block' : 'none';
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        event.target.classList.add('active');

        if (tabName === 'chart') {
            renderChart();
        }
    }

    function renderChart() {
        const ctx = document.getElementById('portfolioChart').getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: {{ chart_labels|tojson }},
                datasets: [{
                    data: {{ chart_data|tojson }},
                    backgroundColor: [
                        '#00d4aa', '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4',
                        '#ffeaa7', '#dfe6e9', '#a29bfe', '#fd79a8', '#fdcb6e'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#fff' }
                    }
                }
            }
        });
    }
</script>
{% endblock %}
"""

TRANSACTIONS_TEMPLATE = """
{% extends "base" %}
{% block title %}Transaction History - OpenStock{% endblock %}
{% block content %}
<div class="card">
    <div class="card-header">
        <h2 class="card-title">Transaction History</h2>
    </div>
    {% if transactions %}
    <table class="table">
        <thead>
            <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Symbol</th>
                <th>Shares</th>
                <th>Price</th>
                <th>Total</th>
            </tr>
        </thead>
        <tbody>
            {% for tx in transactions %}
            <tr>
                <td>{{ tx.date }}</td>
                <td>
                    <span class="{{ 'positive' if tx.type == 'BUY' else 'negative' }}">
                        {{ tx.type }}
                    </span>
                </td>
                <td><a href="/stock/{{ tx.symbol }}" style="color: #00d4aa; text-decoration: none;"><strong>{{ tx.symbol }}</strong></a></td>
                <td>{{ tx.shares }}</td>
                <td>${{ "%.2f"|format(tx.price) }}</td>
                <td>${{ "%.2f"|format(tx.total) }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
    {% else %}
    <div style="text-align: center; padding: 3rem;">
        <h3 style="margin-bottom: 1rem;">No Transactions Yet</h3>
        <p style="color: rgba(255,255,255,0.6);">Your transaction history will appear here</p>
    </div>
    {% endif %}
</div>
{% endblock %}
"""

STOCK_DETAIL_TEMPLATE = """
{% extends "base" %}
{% block title %}{{ symbol }} - {{ name }} - OpenStock{% endblock %}
{% block content %}
<div class="card">
    <div class="stock-detail-header">
        <div class="stock-detail-info">
            <h1>{{ symbol }}</h1>
            <p style="color: rgba(255,255,255,0.6); font-size: 1.125rem;">{{ name }}</p>
            <p style="color: rgba(255,255,255,0.4); font-size: 0.875rem;">{{ sector }}</p>
        </div>
        <div class="stock-detail-price-section">
            <div class="stock-detail-price">${{ "%.2f"|format(price) }}</div>
            <div class="stock-detail-change {{ 'positive' if change >= 0 else 'negative' }}">
                {{ '▲' if change >= 0 else '▼' }} ${{ "%.2f"|format(change_amount|abs) }} ({{ "%.2f"|format(change|abs) }}%)
            </div>
        </div>
    </div>

    <div class="stock-stats">
        <div class="stat-card">
            <div class="stat-label">Open</div>
            <div class="stat-value">${{ "%.2f"|format(stats.open) if stats else price }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">High</div>
            <div class="stat-value">${{ "%.2f"|format(stats.high) if stats else price }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Low</div>
            <div class="stat-value">${{ "%.2f"|format(stats.low) if stats else price }}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Volume</div>
            <div class="stat-value">{{ (stats.volumes[-1] / 1000000)|round(1) }}M</div>
        </div>
    </div>

    {% if history %}
    <div class="time-range-selector">
        <button class="time-range-btn {{ 'active' if period == '1d' else '' }}" onclick="loadChart('1d')">1D</button>
        <button class="time-range-btn {{ 'active' if period == '5d' else '' }}" onclick="loadChart('5d')">5D</button>
        <button class="time-range-btn {{ 'active' if period == '1mo' else '' }}" onclick="loadChart('1mo')">1M</button>
        <button class="time-range-btn {{ 'active' if period == '3mo' else '' }}" onclick="loadChart('3mo')">3M</button>
        <button class="time-range-btn {{ 'active' if period == '1y' else '' }}" onclick="loadChart('1y')">1Y</button>
        <button class="time-range-btn {{ 'active' if period == '5y' else '' }}" onclick="loadChart('5y')">5Y</button>
    </div>
    <div class="chart-container" style="height: 400px;">
        <canvas id="priceChart"></canvas>
    </div>
    {% endif %}
</div>

{% if current_user.is_authenticated %}
<div class="card">
    <h2 class="card-title" style="margin-bottom: 1.5rem;">Trade {{ symbol }}</h2>
    <div class="buy-sell-form">
        <div class="form-group">
            <label>Shares</label>
            <input type="number" id="trade-shares" min="1" value="1">
        </div>
        <form action="/buy" method="POST" style="flex: 1;">
            <input type="hidden" name="symbol" value="{{ symbol }}">
            <input type="hidden" name="price" value="{{ price }}">
            <input type="hidden" name="shares" id="buy-shares" value="1">
            <button type="submit" class="btn btn-primary" style="width: 100%;">Buy</button>
        </form>
        {% if portfolio and symbol in portfolio %}
        <form action="/sell" method="POST" style="flex: 1;">
            <input type="hidden" name="symbol" value="{{ symbol }}">
            <input type="hidden" name="price" value="{{ price }}">
            <input type="hidden" name="shares" id="sell-shares" value="1">
            <button type="submit" class="btn btn-danger" style="width: 100%;">Sell</button>
        </form>
        {% endif %}
    </div>
    {% if portfolio and symbol in portfolio %}
    <p style="margin-top: 1rem; color: rgba(255,255,255,0.6);">You own {{ portfolio[symbol].shares }} shares</p>
    {% endif %}
</div>
{% endif %}

<script>
    let currentSymbol = '{{ symbol }}';
    let chartInstance = null;

    function loadChart(period) {
        fetch(`/api/history/${currentSymbol}?period=${period}`)
            .then(res => res.json())
            .then(data => {
                if (data.dates && data.dates.length > 0) {
                    renderChart(data, period);
                    document.querySelectorAll('.time-range-btn').forEach(btn => {
                        btn.classList.toggle('active', btn.textContent.toLowerCase() === period);
                    });
                }
            });
    }

    function renderChart(data, period) {
        const ctx = document.getElementById('priceChart').getContext('2d');

        if (chartInstance) {
            chartInstance.destroy();
        }

        const isUp = data.closes[data.closes.length - 1] >= data.closes[0];
        const color = isUp ? '#00d4aa' : '#ff4757';

        chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: [{
                    label: 'Price',
                    data: data.closes,
                    borderColor: color,
                    backgroundColor: color + '20',
                    fill: true,
                    tension: 0.4,
                    pointRadius: period === '1d' || period === '5d' ? 2 : 0,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return '$' + context.parsed.y.toFixed(2);
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255,255,255,0.1)'
                        },
                        ticks: {
                            color: 'rgba(255,255,255,0.6)',
                            maxTicksLimit: 8
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255,255,255,0.1)'
                        },
                        ticks: {
                            color: 'rgba(255,255,255,0.6)',
                            callback: function(value) {
                                return '$' + value.toFixed(0);
                            }
                        }
                    }
                }
            }
        });
    }

    // Sync share inputs
    document.getElementById('trade-shares').addEventListener('input', function(e) {
        document.getElementById('buy-shares').value = e.target.value;
        if (document.getElementById('sell-shares')) {
            document.getElementById('sell-shares').value = e.target.value;
        }
    });

    // Initial chart render
    {% if history %}
    renderChart({{ history|tojson }}, '{{ period }}');
    {% endif %}
</script>
{% endblock %}
"""

app.template_filters['json'] = lambda v: json.dumps(v)
app.template_filters['abs'] = lambda v: abs(v) if v else 0


@app.route('/')
def index():
    fetch_real_time_prices()
    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', INDEX_TEMPLATE)
    return render_template_string(template, stocks=STOCKS, prices=current_prices, changes=price_changes)


@app.route('/stock/<symbol>')
def stock_detail(symbol):
    symbol = symbol.upper()

    # Add unknown stocks on-the-fly
    if symbol not in STOCKS:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            name = ticker.info.get('longName', ticker.info.get('shortName', symbol))
            sector = ticker.info.get('sector', 'Unknown')
            price = info.last_price if hasattr(info, 'last_price') and info.last_price else 0
            STOCKS[symbol] = {'name': name, 'base_price': price, 'sector': sector}
            current_prices[symbol] = price
            price_changes[symbol] = 0.0
        except:
            return "Stock not found", 404
    else:
        name = STOCKS[symbol]['name']
        sector = STOCKS[symbol]['sector']

    fetch_real_time_prices()
    price = current_prices.get(symbol, STOCKS[symbol]['base_price'])
    change = price_changes.get(symbol, 0)
    change_amount = price * (change / 100) if price else 0

    # Get history for chart
    period = request.args.get('period', '1mo')
    history = fetch_stock_history(symbol, period)

    # Get user portfolio
    portfolio = portfolio_db.get(current_user.id, {}) if current_user.is_authenticated else {}

    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', STOCK_DETAIL_TEMPLATE)
    return render_template_string(
        template,
        symbol=symbol,
        name=name,
        sector=sector,
        price=price,
        change=change,
        change_amount=change_amount,
        stats=history,
        history=history,
        period=period,
        portfolio=portfolio
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if user exists
        for user in users_db.values():
            if user.email == email:
                flash('Email already registered', 'error')
                return redirect(url_for('register'))

        user_id = str(len(users_db) + 1)
        user = User(user_id, username, email, generate_password_hash(password))
        users_db[user_id] = user
        portfolio_db[user_id] = {}
        transactions_db[user_id] = []

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', REGISTER_TEMPLATE)
    return render_template_string(template)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        for user in users_db.values():
            if user.email == email and check_password_hash(user.password_hash, password):
                login_user(user)
                return redirect(url_for('index'))

        flash('Invalid email or password', 'error')
        return redirect(url_for('login'))

    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', LOGIN_TEMPLATE)
    return render_template_string(template)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/buy', methods=['POST'])
@login_required
def buy_stock():
    symbol = request.form.get('symbol')
    price = float(request.form.get('price'))
    shares = int(request.form.get('shares'))

    total_cost = price * shares

    if total_cost > current_user.cash_balance:
        flash('Insufficient funds', 'error')
        return redirect(url_for('index'))

    # Update cash balance
    current_user.cash_balance -= total_cost

    # Update portfolio
    portfolio = portfolio_db.get(current_user.id, {})
    if symbol in portfolio:
        total_shares = portfolio[symbol]['shares'] + shares
        total_cost_basis = (portfolio[symbol]['avg_cost'] * portfolio[symbol]['shares']) + (price * shares)
        portfolio[symbol] = {
            'shares': total_shares,
            'avg_cost': total_cost_basis / total_shares
        }
    else:
        portfolio[symbol] = {
            'shares': shares,
            'avg_cost': price
        }
    portfolio_db[current_user.id] = portfolio

    # Record transaction
    tx = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'type': 'BUY',
        'symbol': symbol,
        'shares': shares,
        'price': price,
        'total': total_cost
    }
    transactions_db.setdefault(current_user.id, []).insert(0, tx)

    flash(f'Bought {shares} shares of {symbol} at ${price:.2f}', 'success')
    return redirect(url_for('portfolio'))


@app.route('/sell', methods=['POST'])
@login_required
def sell_stock():
    symbol = request.form.get('symbol')
    price = float(request.form.get('price'))
    shares = int(request.form.get('shares'))

    portfolio = portfolio_db.get(current_user.id, {})

    if symbol not in portfolio or portfolio[symbol]['shares'] < shares:
        flash('Insufficient shares', 'error')
        return redirect(url_for('portfolio'))

    total_proceeds = price * shares

    # Update cash balance
    current_user.cash_balance += total_proceeds

    # Update portfolio
    portfolio[symbol]['shares'] -= shares
    if portfolio[symbol]['shares'] == 0:
        del portfolio[symbol]
    portfolio_db[current_user.id] = portfolio

    # Record transaction
    tx = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'type': 'SELL',
        'symbol': symbol,
        'shares': shares,
        'price': price,
        'total': total_proceeds
    }
    transactions_db.setdefault(current_user.id, []).insert(0, tx)

    flash(f'Sold {shares} shares of {symbol} at ${price:.2f}', 'success')
    return redirect(url_for('portfolio'))


@app.route('/portfolio')
@login_required
def portfolio():
    portfolio = portfolio_db.get(current_user.id, {})
    fetch_real_time_prices()

    # Calculate totals
    invested = 0
    total_value = current_user.cash_balance

    chart_labels = ['Cash']
    chart_data = [current_user.cash_balance]

    for symbol, holding in portfolio.items():
        value = holding['shares'] * current_prices.get(symbol, holding['avg_cost'])
        total_value += value
        invested += holding['avg_cost'] * holding.shares
        chart_labels.append(symbol)
        chart_data.append(value)

    total_return = ((total_value - 10000) / 10000) * 100 if total_value > 0 else 0

    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', PORTFOLIO_TEMPLATE)
    return render_template_string(
        template,
        portfolio=portfolio,
        prices=current_prices,
        total_value=total_value,
        invested=invested,
        total_return=total_return,
        chart_labels=chart_labels,
        chart_data=chart_data
    )


@app.route('/transactions')
@login_required
def transactions():
    txs = transactions_db.get(current_user.id, [])
    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', TRANSACTIONS_TEMPLATE)
    return render_template_string(template, transactions=txs)


@app.route('/api/prices')
def api_prices():
    fetch_real_time_prices()
    return jsonify({
        'prices': current_prices,
        'changes': price_changes,
        'stocks': STOCKS
    })


@app.route('/api/search')
def api_search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'results': []})

    results = search_stocks(query)
    return jsonify({'results': results})


@app.route('/api/history/<symbol>')
def api_history(symbol):
    period = request.args.get('period', '1mo')
    history = fetch_stock_history(symbol.upper(), period)
    return jsonify(history or {})


# ==================== NEW FEATURES ====================

@app.route('/watchlist')
@login_required
def watchlist():
    """Display user's watchlist"""
    user_id = current_user.get_id()
    watchlist = watchlist_db.get(user_id, [])

    watchlist_data = []
    for symbol in watchlist:
        if symbol in STOCKS:
            watchlist_data.append({
                'symbol': symbol,
                'name': STOCKS[symbol]['name'],
                'price': current_prices.get(symbol, 0),
                'change': price_changes.get(symbol, 0),
                'sector': STOCKS[symbol]['sector']
            })

    # Calculate total portfolio value and cash
    portfolio = portfolio_db.get(user_id, {})
    cash = users_db.get(user_id, {}).get('cash', 100000)
    portfolio_value = sum(
        holdings['shares'] * current_prices.get(symbol, 0)
        for symbol, holdings in portfolio.items()
    )

    total_value = cash + portfolio_value

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Watchlist - Robinhood Clone</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #fff; }}
        .header {{ background: #1a1a1a; padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; }}
        .logo {{ font-size: 24px; font-weight: bold; color: #00c805; }}
        .nav {{ display: flex; gap: 20px; }}
        .nav a {{ color: #888; text-decoration: none; transition: color 0.2s; }}
        .nav a:hover, .nav a.active {{ color: #fff; }}
        .user-info {{ color: #888; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
        .page-title {{ font-size: 32px; margin-bottom: 30px; }}
        .summary-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 40px; }}
        .card {{ background: #1a1a1a; padding: 20px; border-radius: 12px; border: 1px solid #333; }}
        .card-label {{ color: #888; font-size: 14px; margin-bottom: 8px; }}
        .card-value {{ font-size: 28px; font-weight: bold; }}
        .positive {{ color: #00c805; }}
        .negative {{ color: #ff4444; }}
        .watchlist-grid {{ display: grid; gap: 12px; }}
        .watchlist-item {{ background: #1a1a1a; padding: 20px; border-radius: 12px; border: 1px solid #333; display: flex; justify-content: space-between; align-items: center; transition: background 0.2s; }}
        .watchlist-item:hover {{ background: #252525; }}
        .stock-info {{ display: flex; flex-direction: column; gap: 4px; }}
        .stock-symbol {{ font-size: 18px; font-weight: bold; }}
        .stock-name {{ color: #888; font-size: 14px; }}
        .stock-price {{ text-align: right; }}
        .price-value {{ font-size: 18px; font-weight: bold; }}
        .price-change {{ font-size: 14px; }}
        .stock-actions {{ display: flex; gap: 10px; }}
        .btn {{ padding: 8px 16px; border-radius: 8px; border: none; cursor: pointer; font-weight: 600; transition: all 0.2s; }}
        .btn-buy {{ background: #00c805; color: #000; }}
        .btn-buy:hover {{ background: #00a804; }}
        .btn-remove {{ background: #333; color: #fff; }}
        .btn-remove:hover {{ background: #444; }}
        .empty-state {{ text-align: center; padding: 60px; color: #888; }}
        .empty-state h3 {{ margin-bottom: 10px; color: #fff; }}
        .add-form {{ background: #1a1a1a; padding: 20px; border-radius: 12px; margin-top: 30px; }}
        .add-form h3 {{ margin-bottom: 15px; }}
        .form-group {{ display: flex; gap: 10px; }}
        .form-group input {{ flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #333; background: #0a0a0a; color: #fff; }}
        .form-group button {{ padding: 12px 24px; border-radius: 8px; border: none; background: #00c805; color: #000; font-weight: bold; cursor: pointer; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">Robinhood Clone</div>
        <nav class="nav">
            <a href="/">Home</a>
            <a href="/portfolio">Portfolio</a>
            <a href="/watchlist" class="active">Watchlist</a>
            <a href="/market">Market</a>
            <a href="/transactions">Transactions</a>
        </nav>
        <div class="user-info">
            Cash: <span class="positive">${total_value:,.2f}</span>
            <a href="/logout" style="color: #888; margin-left: 20px;">Logout</a>
        </div>
    </div>
    <div class="container">
        <h1 class="page-title">Your Watchlist</h1>
        <div class="summary-cards">
            <div class="card">
                <div class="card-label">Stocks Watching</div>
                <div class="card-value">{len(watchlist_data)}</div>
            </div>
            <div class="card">
                <div class="card-label">Portfolio Value</div>
                <div class="card-value">${portfolio_value:,.2f}</div>
            </div>
            <div class="card">
                <div class="card-label">Available Cash</div>
                <div class="card-value">${cash:,.2f}</div>
            </div>
        </div>
        {"<div class='empty-state'><h3>No stocks in watchlist</h3><p>Add stocks to track their prices</p></div>" if not watchlist_data else ""}
        <div class="watchlist-grid">
            {"".join(f'''
            <div class="watchlist-item">
                <div class="stock-info">
                    <span class="stock-symbol">{item['symbol']}</span>
                    <span class="stock-name">{item['name']} - {item['sector']}</span>
                </div>
                <div class="stock-price">
                    <div class="price-value">${item['price']:,.2f}</div>
                    <div class="price-change {'positive' if item['change'] >= 0 else 'negative'}">{item['change']:+.2f}%</div>
                </div>
                <div class="stock-actions">
                    <form action="/buy" method="POST" style="display:inline;">
                        <input type="hidden" name="symbol" value="{item['symbol']}">
                        <button type="submit" class="btn btn-buy">Buy</button>
                    </form>
                    <form action="/api/watchlist/remove" method="POST" style="display:inline;">
                        <input type="hidden" name="symbol" value="{item['symbol']}">
                        <button type="submit" class="btn btn-remove">Remove</button>
                    </form>
                </div>
            </div>''' for item in watchlist_data)}
        </div>
        <div class="add-form">
            <h3>Add to Watchlist</h3>
            <form class="form-group" action="/api/watchlist/add" method="POST">
                <input type="text" name="symbol" placeholder="Enter stock symbol (e.g., AAPL)" required style="text-transform: uppercase;">
                <button type="submit">Add</button>
            </form>
        </div>
    </div>
</body>
</html>
"""


@app.route('/api/watchlist/add', methods=['POST'])
@login_required
def add_to_watchlist():
    """Add a stock to user's watchlist"""
    symbol = request.form.get('symbol', '').upper().strip()

    if not symbol:
        flash('Please enter a stock symbol')
        return redirect('/watchlist')

    if symbol not in STOCKS:
        flash(f'Stock {symbol} not found')
        return redirect('/watchlist')

    user_id = current_user.get_id()
    if user_id not in watchlist_db:
        watchlist_db[user_id] = []

    if symbol in watchlist_db[user_id]:
        flash(f'{symbol} is already in your watchlist')
        return redirect('/watchlist')

    watchlist_db[user_id].append(symbol)
    flash(f'Added {symbol} to your watchlist')
    return redirect('/watchlist')


@app.route('/api/watchlist/remove', methods=['POST'])
@login_required
def remove_from_watchlist():
    """Remove a stock from user's watchlist"""
    symbol = request.form.get('symbol', '').upper().strip()

    user_id = current_user.get_id()
    if user_id in watchlist_db and symbol in watchlist_db[user_id]:
        watchlist_db[user_id].remove(symbol)
        flash(f'Removed {symbol} from your watchlist')

    return redirect('/watchlist')


@app.route('/market')
@login_required
def market():
    """Market overview dashboard with top movers and sector performance"""
    # Get top gainers and losers
    sorted_by_change = sorted(
        [(symbol, data['name'], current_prices.get(symbol, 0), price_changes.get(symbol, 0), data['sector'])
         for symbol, data in STOCKS.items()],
        key=lambda x: x[3],
        reverse=True
    )

    top_gainers = sorted_by_change[:5]
    top_losers = sorted_by_change[-5:][::-1]

    # Sector performance
    sectors = {}
    for symbol, data in STOCKS.items():
        sector = data['sector']
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append(price_changes.get(symbol, 0))

    sector_performance = []
    for sector, changes in sectors.items():
        avg_change = sum(changes) / len(changes) if changes else 0
        sector_performance.append({
            'sector': sector,
            'change': avg_change,
            'count': len(changes)
        })
    sector_performance.sort(key=lambda x: x['change'], reverse=True)

    # Calculate portfolio stats
    user_id = current_user.get_id()
    portfolio = portfolio_db.get(user_id, {})
    cash = users_db.get(user_id, {}).get('cash', 100000)
    portfolio_value = sum(
        holdings['shares'] * current_prices.get(symbol, 0)
        for symbol, holdings in portfolio.items()
    )
    total_value = cash + portfolio_value

    # All stocks sorted by performance
    all_stocks = [(symbol, data['name'], current_prices.get(symbol, 0), price_changes.get(symbol, 0), data['sector'])
                  for symbol, data in STOCKS.items()]

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Market Overview - Robinhood Clone</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #fff; }}
        .header {{ background: #1a1a1a; padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; }}
        .logo {{ font-size: 24px; font-weight: bold; color: #00c805; }}
        .nav {{ display: flex; gap: 20px; }}
        .nav a {{ color: #888; text-decoration: none; transition: color 0.2s; }}
        .nav a:hover, .nav a.active {{ color: #fff; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 40px 20px; }}
        .page-title {{ font-size: 32px; margin-bottom: 30px; }}
        .market-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-bottom: 40px; }}
        @media (max-width: 900px) {{ .market-grid {{ grid-template-columns: 1fr; }} }}
        .section {{ background: #1a1a1a; padding: 24px; border-radius: 12px; border: 1px solid #333; }}
        .section-title {{ font-size: 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }}
        .positive {{ color: #00c805; }}
        .negative {{ color: #ff4444; }}
        .stock-list {{ display: flex; flex-direction: column; gap: 12px; }}
        .stock-row {{ display: flex; justify-content: space-between; align-items: center; padding: 12px; background: #252525; border-radius: 8px; transition: background 0.2s; }}
        .stock-row:hover {{ background: #2a2a2a; }}
        .stock-symbol {{ font-weight: bold; font-size: 16px; }}
        .stock-name {{ color: #888; font-size: 13px; }}
        .stock-price {{ text-align: right; }}
        .price-value {{ font-weight: bold; }}
        .price-change {{ font-size: 13px; }}
        .sector-list {{ display: flex; flex-direction: column; gap: 10px; }}
        .sector-row {{ display: flex; justify-content: space-between; align-items: center; padding: 12px; background: #252525; border-radius: 8px; }}
        .sector-name {{ font-weight: 600; }}
        .sector-count {{ color: #666; font-size: 12px; margin-left: 8px; }}
        .full-stocks {{ margin-top: 40px; }}
        .stocks-table {{ width: 100%; border-collapse: collapse; }}
        .stocks-table th {{ text-align: left; padding: 12px; color: #888; border-bottom: 1px solid #333; }}
        .stocks-table td {{ padding: 14px 12px; border-bottom: 1px solid #252525; }}
        .stocks-table tr:hover {{ background: #1f1f1f; }}
        .btn {{ padding: 8px 16px; border-radius: 8px; border: none; cursor: pointer; font-weight: 600; transition: all 0.2s; }}
        .btn-watch {{ background: #333; color: #fff; }}
        .btn-watch:hover {{ background: #444; }}
        .btn-buy {{ background: #00c805; color: #000; }}
        .btn-buy:hover {{ background: #00a804; }}
        .action-buttons {{ display: flex; gap: 8px; }}
        .user-info {{ color: #888; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">Robinhood Clone</div>
        <nav class="nav">
            <a href="/">Home</a>
            <a href="/portfolio">Portfolio</a>
            <a href="/watchlist">Watchlist</a>
            <a href="/market" class="active">Market</a>
            <a href="/transactions">Transactions</a>
        </nav>
        <div class="user-info">
            Total: <span class="positive">${total_value:,.2f}</span>
            <a href="/logout" style="color: #888; margin-left: 20px;">Logout</a>
        </div>
    </div>
    <div class="container">
        <h1 class="page-title">Market Overview</h1>

        <div class="market-grid">
            <div class="section">
                <div class="section-title">
                    <span>Top Gainers</span>
                    <span class="positive">+</span>
                </div>
                <div class="stock-list">
                    {"".join(f'''
                    <div class="stock-row">
                        <div>
                            <div class="stock-symbol">{item[0]}</div>
                            <div class="stock-name">{item[1]}</div>
                        </div>
                        <div class="stock-price">
                            <div class="price-value">${item[2]:,.2f}</div>
                            <div class="price-change positive">{item[3]:+.2f}%</div>
                        </div>
                    </div>''' for item in top_gainers)}
                </div>
            </div>

            <div class="section">
                <div class="section-title">
                    <span>Top Losers</span>
                    <span class="negative">-</span>
                </div>
                <div class="stock-list">
                    {"".join(f'''
                    <div class="stock-row">
                        <div>
                            <div class="stock-symbol">{item[0]}</div>
                            <div class="stock-name">{item[1]}</div>
                        </div>
                        <div class="stock-price">
                            <div class="price-value">${item[2]:,.2f}</div>
                            <div class="price-change negative">{item[3]:+.2f}%</div>
                        </div>
                    </div>''' for item in top_losers)}
                </div>
            </div>
        </div>

        <div class="section" style="margin-bottom: 40px;">
            <div class="section-title">Sector Performance</div>
            <div class="sector-list">
                {"".join(f'''
                <div class="sector-row">
                    <div>
                        <span class="sector-name">{item['sector']}</span>
                        <span class="sector-count">{item['count']} stocks</span>
                    </div>
                    <div class="price-change {'positive' if item['change'] >= 0 else 'negative'}">
                        {item['change']:+.2f}%
                    </div>
                </div>''' for item in sector_performance)}
            </div>
        </div>

        <div class="section full-stocks">
            <div class="section-title">All Stocks</div>
            <table class="stocks-table">
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>Name</th>
                        <th>Sector</th>
                        <th>Price</th>
                        <th>Change</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(f'''
                    <tr>
                        <td><strong>{item[0]}</strong></td>
                        <td>{item[1]}</td>
                        <td>{item[4]}</td>
                        <td>${item[2]:,.2f}</td>
                        <td class="{'positive' if item[3] >= 0 else 'negative'}">{item[3]:+.2f}%</td>
                        <td>
                            <div class="action-buttons">
                                <form action="/api/watchlist/add" method="POST">
                                    <input type="hidden" name="symbol" value="{item[0]}">
                                    <button type="submit" class="btn btn-watch">Watch</button>
                                </form>
                                <form action="/buy" method="POST">
                                    <input type="hidden" name="symbol" value="{item[0]}">
                                    <button type="submit" class="btn btn-buy">Buy</button>
                                </form>
                            </div>
                        </td>
                    </tr>''' for item in all_stocks)}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""


if __name__ == '__main__':
    # Initial fetch of real prices
    print("Fetching initial stock prices...")
    fetch_real_time_prices()
    app.run(debug=True, host='0.0.0.0', port=5000)
