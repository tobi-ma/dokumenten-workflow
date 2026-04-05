#!/usr/bin/env python3
"""Portfolio Price Fetcher - clean sources per ticker"""
import csv, json, os, time
from datetime import datetime
import urllib.request

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
PORTFOLIO_FILE = os.path.join(DATA_DIR, "aktienliste.csv")
HISTORY_FILE = os.path.join(DATA_DIR, "price_history.csv")
FH_KEY = "d739lmpr01qjjol288egd739lmpr01qjjol288f0"

# Source: Finnhub (USD prices)
FH_TICKERS = {'AAPL', 'AMD', 'MSFT', 'NVDA', 'TSLA', 'SBUX', 'FCX', 'BRK.B'}

# Source: Stooq (EUR prices)
SQ_TICKERS = {'IFX', 'NDA', 'SAP', 'PBB', 'NDQ', 'SP500', 'WOOMO', 'EUMO'}

# Source: Yahoo Finance chart (native currency)
YH_TICKERS = {'SHEL': 'SHEL.L', 'BYD': '1211.HK'}

# FX rates for Yahoo currency conversion
GBP_EUR = 1.18   # fallback
HKD_EUR = 0.12   # fallback

def get_fx_rate(from_ccy, to_ccy):
    pair = f"{from_ccy}{to_ccy}=X"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair}?interval=1d&range=1d"
    try:
        d = json.loads(urllib.request.urlopen(
            urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=10).read())
        c = d['chart']['result'][0]['indicators']['quote'][0]['close']
        return c[-1] if c and c[-1] else None
    except: return None

def finnhub_quote(ticker):
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FH_KEY}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode())
        if d.get('c', 0) > 0:
            return {'price': d['c'], 'change': d['d'], 'change_pct': d['dp'], 'source': 'fh'}
    except: pass
    return None

def stooq_quote(sym):
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            lines = r.read().decode().strip().split('\n')
        if len(lines) >= 2:
            p = lines[-1].split(',')
            if len(p) >= 5: return {'price': float(p[4]), 'source': 'sq'}
    except: pass
    return None

def yahoo_chart(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode())
        result = d['chart']['result'][0]
        closes = result['indicators']['quote'][0]['close']
        ts = result['timestamp']
        if closes and closes[-1]:
            dt = datetime.fromtimestamp(ts[-1])
            return {'date': dt.strftime('%Y-%m-%d'), 'price': closes[-1], 'source': 'yh'}
    except: pass
    return None

def load_last():
    last = {}
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            for row in csv.DictReader(f):
                t = row['ticker']
                ts = row.get('timestamp', '')
                if t not in last or ts > last[t].get('ts', ''):
                    last[t] = {'ts': ts, 'price': row.get('price', '')}
    return last

def save(prices, ts):
    file_exists = os.path.getsize(HISTORY_FILE) > 0
    with open(HISTORY_FILE, 'a', newline='') as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(['timestamp','isin','ticker','price','change','change_pct','volume'])
        for t, d in prices.items():
            if d.get('price'):
                w.writerow([ts, d.get('isin', ''), t, d['price'],
                           d.get('change', ''), d.get('change_pct', ''), ''])

def main():
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    stocks = list(csv.DictReader(open(PORTFOLIO_FILE)))
    prev = load_last()
    results, alerts = {}, []

    print(f"Fetching {len(stocks)} stocks at {ts}...\n")

    for s in stocks:
        tk, isin = s['ticker'], s['isin']
        d = None

        # Finnhub (USD)
        if tk in FH_TICKERS:
            d = finnhub_quote(tk)
        
        # Stooq (EUR)
        elif tk in SQ_TICKERS:
            stooq_sym = {
                'IFX': 'IFX.DE', 'NDA': 'NDA.DE', 'SAP': 'SAP.DE', 'PBB': 'PBB.DE',
                'NDQ': 'SXR8.DE', 'SP500': 'EUNL.DE', 'WOOMO': 'EUNA.DE', 'EUMO': 'EUNA.DE'
            }.get(tk, f'{tk}.DE')
            d = stooq_quote(stooq_sym)
        
        # Yahoo Finance (native currency)
        elif tk in YH_TICKERS:
            d = yahoo_chart(YH_TICKERS[tk])
            if d and d.get('price'):
                if tk == 'SHEL' and d['price'] > 100:  # GBp → EUR
                    gbp = d['price'] / 100
                    rate = get_fx_rate('GBPEUR', 'X') or GBP_EUR
                    d['price'] = round(gbp * rate, 2)
                elif tk == 'BYD' and d['price'] > 100:  # HKD → EUR
                    hkd_eur = get_fx_rate('HKDEUR', 'X') or HKD_EUR
                    d['price'] = round(d['price'] * hkd_eur, 2)
                del d['date']  # remove extra key
        
        if not d or not d.get('price'):
            results[tk] = {'isin': isin, 'name': s['name'], 'priority': s.get('priority', ''), 'error': True}
            print(f"  ⚠️  {tk}: no data")
            continue

        # Change vs previous
        lp = prev.get(tk, {})
        lp_p = float(lp.get('price', 0)) or None
        if lp_p:
            ch = round(d['price'] - lp_p, 4)
            pct = round(ch / lp_p * 100, 4)
            d['change'] = ch; d['change_pct'] = pct
            if abs(pct) >= 2.5:
                alerts.append({'ticker': tk, 'name': s['name'], 'price': d['price'], 'change': ch, 'change_pct': pct})

        d['isin'] = isin; d['name'] = s['name']; d['priority'] = s.get('priority', '')
        results[tk] = d

        prio = "⭐" if d.get('priority') == '1' else " "
        ch = d.get('change'); pct = d.get('change_pct')
        cs = f"{ch:+.2f}" if ch is not None else "-"
        ps = f"{pct:+.2f}%" if pct is not None else "-"
        print(f"  {tk:<8} {prio} {d['price']:>9.2f}  {cs:>8}  {ps:>8}  [{d['source']}]")
        time.sleep(0.25)

    save(results, ts)

    if alerts:
        print(f"\n🚨 ALERTS (|Δ%| ≥ 2.5%):")
        for a in sorted(alerts, key=lambda x: abs(x['change_pct']), reverse=True):
            e = "📈" if a['change_pct'] > 0 else "📉"
            print(f"  {e} {a['ticker']}: {a['price']:.2f} ({a['change_pct']:+.2f}%) | Δ {a['change']:+.2f}")

    ok = sum(1 for r in results.values() if not r.get('error'))
    print(f"\n✓ {ok}/{len(stocks)} prices saved")

if __name__ == '__main__':
    main()
