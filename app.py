"""
Robinhood-style Investment Platform
A modern stock trading simulation platform with authentication,
portfolio tracking, real-time price simulation, and transaction history.
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json
import random
import time
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'robinhood-clone-secret-key-2026'

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# In-memory data storage (in production, use a database)
users_db = {}
portfolio_db = {}
transactions_db = {}

# Stock price simulation data
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
}

# Current stock prices (simulated real-time)
current_prices = {symbol: data['base_price'] for symbol, data in STOCKS.items()}

def simulate_price_change():
    """Simulate real-time price changes"""
    global current_prices
    for symbol in current_prices:
        change_percent = random.uniform(-0.5, 0.5)  # -0.5% to +0.5% change
        current_prices[symbol] *= (1 + change_percent / 100)
        current_prices[symbol] = round(current_prices[symbol], 2)


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
        // Auto-refresh prices every 3 seconds
        {% if request.endpoint == 'index' or request.endpoint == 'portfolio' %}
        setInterval(() => {
            fetch('/api/prices')
                .then(res => res.json())
                .then(data => {
                    document.querySelectorAll('.stock-price').forEach(el => {
                        const symbol = el.dataset.symbol;
                        if (data[symbol]) {
                            el.textContent = '$' + data[symbol].toFixed(2);
                        }
                    });
                });
        }, 3000);
        {% endif %}
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
        <span class="price-updating" style="color: rgba(255,255,255,0.6);">● Live Prices</span>
    </div>
    <div class="stock-grid">
        {% for symbol, data in stocks.items() %}
        <div class="stock-card">
            <div class="stock-symbol">{{ symbol }}</div>
            <div class="stock-name">{{ data.name }}</div>
            <div class="stock-price" data-symbol="{{ symbol }}">${{ "%.2f"|format(prices[symbol]) }}</div>
            <div class="stock-change">
                <span class="positive">▲ {{ data.sector }}</span>
            </div>
            {% if current_user.is_authenticated %}
            <div style="margin-top: 1rem; display: flex; gap: 0.5rem;">
                <form action="/buy" method="POST" style="flex: 1;">
                    <input type="hidden" name="symbol" value="{{ symbol }}">
                    <input type="hidden" name="price" value="{{ prices[symbol] }}">
                    <input type="number" name="shares" min="1" value="1" style="width: 60px; padding: 0.5rem; border-radius: 4px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff;">
                    <button type="submit" class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 0.875rem;">Buy</button>
                </form>
            </div>
            {% endif %}
        </div>
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
                    <td><strong style="color: #00d4aa;">{{ symbol }}</strong></td>
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
                <td><strong style="color: #00d4aa;">{{ tx.symbol }}</strong></td>
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

app.template_filters('json') = lambda v: json.dumps(v)


@app.route('/')
def index():
    simulate_price_change()
    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', INDEX_TEMPLATE)
    return render_template_string(template, stocks=STOCKS, prices=current_prices)


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
    simulate_price_change()

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
    simulate_price_change()
    return jsonify(current_prices)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
