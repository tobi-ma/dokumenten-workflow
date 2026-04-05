#!/usr/bin/env python3
"""
Portfolio Report Generator
Combines price data + news + trend analysis for scheduled reports
"""
import csv
import json
import os
import sys
from datetime import datetime, timedelta
import subprocess

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
PORTFOLIO_FILE = os.path.join(DATA_DIR, "aktienliste.csv")
HISTORY_FILE = os.path.join(DATA_DIR, "price_history.csv")

def load_portfolio():
    stocks = []
    with open(PORTFOLIO_FILE, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('isin'):
                stocks.append({
                    'name': row['name'],
                    'isin': row['isin'],
                    'ticker': row.get('ticker', ''),
                    'priority': row.get('priority', ''),
                })
    return stocks

def load_price_history(ticker, days=30):
    """Load price history for a ticker"""
    prices = []
    if not os.path.exists(HISTORY_FILE):
        return []
    
    with open(HISTORY_FILE, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Get unique timestamps sorted desc
    by_ts = {}
    for row in rows:
        ts = row.get('timestamp', '')
        t = row.get('ticker', '')
        if t == ticker and row.get('price'):
            if ts not in by_ts:
                by_ts[ts] = float(row.get('price', 0))
    
    # Sort by timestamp
    sorted_prices = sorted(by_ts.items(), key=lambda x: x[0])
    return sorted_prices[-days:]

def calculate_trend(prices):
    """Calculate simple trend from price series"""
    if len(prices) < 5:
        return None, None
    
    # Get first and last prices
    first_price = prices[0][1]
    last_price = prices[-1][1]
    
    if not first_price or not last_price:
        return None, None
    
    total_change = ((last_price - first_price) / first_price) * 100
    
    # Calculate 7-day change if available
    if len(prices) >= 7:
        week_ago_price = prices[-7][1] if len(prices) >= 7 else prices[0][1]
        week_change = ((last_price - week_ago_price) / week_ago_price) * 100 if week_ago_price else None
    else:
        week_change = None
    
    return total_change, week_change

def get_market_context():
    """Get overall market context via web search"""
    try:
        result = subprocess.run(
            ['curl', '-s', '--max-time', '5', 
             'https://stooq.com/q/d/l/?s=^SPX&i=d'],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            last_line = lines[-1]
            parts = last_line.split(',')
            if len(parts) >= 5:
                close = float(parts[4])
                prev = float(parts[1])
                change = ((close - prev) / prev) * 100
                return close, change
    except:
        pass
    return None, None

def generate_report():
    """Generate full portfolio report"""
    now = datetime.now()
    timestamp = now.strftime('%Y-%m-%d %H:%M')
    
    # Determine time of day
    hour = now.hour
    if hour < 10:
        period = "🌅 MORGENS-REPORT"
        news_days = 2
    elif hour < 16:
        period = "☀️ MITTAGS-REPORT"
        news_days = 1
    else:
        period = "🌙 ABEND-REPORT"
        news_days = 1
    
    print(f"\n{'='*70}")
    print(f"📈 PORTFOLIO {period} — {timestamp}")
    print(f"{'='*70}")
    
    # Market context
    spx_close, spx_change = get_market_context()
    if spx_close:
        direction = "📈" if spx_change > 0 else "📉"
        print(f"\n{direction} S&P 500: {spx_close:,.2f} ({spx_change:+.2f}%)")
    
    # Load current prices (from latest history)
    stocks = load_portfolio()
    latest_prices = {}
    
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        for row in rows:
            ticker = row.get('ticker', '')
            ts = row.get('timestamp', '')
            price = row.get('price', '')
            if ticker and price:
                if ticker not in latest_prices or ts > latest_prices[ticker].get('ts', ''):
                    latest_prices[ticker] = {
                        'ts': ts,
                        'price': float(price),
                        'change': row.get('change', ''),
                        'change_pct': row.get('change_pct', ''),
                    }
    
    # Priority positions
    priority = [s for s in stocks if s.get('priority') == '1']
    others = [s for s in stocks if s.get('priority') != '1']
    
    print(f"\n{'─'*70}")
    print(f"⭐ PRIORITY POSITIONS ({len(priority)})")
    print(f"{'─'*70}")
    print(f"{'Ticker':<8} {'Kurs':>10} {'Tages-Änd':>12} {'7T-Trend':>10} {'30T-Trend':>10}")
    print(f"{'─'*70}")
    
    alert_positions = []
    
    for stock in priority:
        ticker = stock['ticker']
        lp = latest_prices.get(ticker, {})
        price = lp.get('price')
        day_change = lp.get('change_pct')
        
        # Calculate trends
        history = load_price_history(ticker, 30)
        trend_30d, trend_7d = calculate_trend(history)
        
        price_str = f"{price:.2f}" if price else "N/A"
        day_str = f"{float(day_change):+.2f}%" if day_change else "-"
        trend_7d_str = f"{trend_7d:+.2f}%" if trend_7d else "-"
        trend_30d_str = f"{trend_30d:+.2f}%" if trend_30d else "-"
        
        # Flag alerts
        flag = ""
        if day_change and abs(float(day_change)) >= 2.5:
            flag = " ⚠️"
            alert_positions.append({
                'ticker': ticker,
                'name': stock['name'],
                'type': 'daily',
                'change': float(day_change)
            })
        if trend_7d and abs(trend_7d) >= 5:
            flag = " 📊"
            alert_positions.append({
                'ticker': ticker,
                'name': stock['name'],
                'type': 'weekly',
                'change': trend_7d
            })
        
        print(f"{ticker:<8} {price_str:>10} {day_str:>12} {trend_7d_str:>10} {trend_30d_str:>10}{flag}")
    
    # Other positions (compact)
    print(f"\n{'─'*70}")
    print(f"📊 OTHER POSITIONS ({len(others)})")
    print(f"{'─'*70}")
    print(f"{'Ticker':<8} {'Kurs':>10} {'Tages-Änd':>12} {'7T-Trend':>10}")
    print(f"{'─'*70}")
    
    for stock in others:
        ticker = stock['ticker']
        lp = latest_prices.get(ticker, {})
        price = lp.get('price')
        day_change = lp.get('change_pct')
        
        history = load_price_history(ticker, 7)
        trend_7d, _ = calculate_trend(history)
        
        price_str = f"{price:.2f}" if price else "N/A"
        day_str = f"{float(day_change):+.2f}%" if day_change else "-"
        trend_7d_str = f"{trend_7d:+.2f}%" if trend_7d else "-"
        
        print(f"{ticker:<8} {price_str:>10} {day_str:>12} {trend_7d_str:>10}")
    
    # Alerts summary
    if alert_positions:
        print(f"\n{'─'*70}")
        print(f"🚨 ALERTS")
        print(f"{'─'*70}")
        for a in sorted(alert_positions, key=lambda x: abs(x['change']), reverse=True):
            emoji = "📈" if a['change'] > 0 else "📉"
            print(f"{emoji} {a['ticker']} ({a['name']}): {a['change']:+.2f}% ({a['type']})")
    
    print(f"\n{'='*70}")
    print("💡 Nächster Report: 8:30 / 14:00 / 19:00 Uhr")
    print("📌 Vollständige News-Analyse folgt separat.")
    
    return alert_positions

if __name__ == '__main__':
    generate_report()
