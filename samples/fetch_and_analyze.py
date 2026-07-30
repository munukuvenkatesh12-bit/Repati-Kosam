#!/usr/bin/env python3
"""
Fetch 6-month OHLCV data and run technical analysis for all 9 watchlist stocks.
Outputs a single JSON file consumed by the interactive dashboard.

Technical Analysis Algorithms:
1. Support/Resistance — Fractal pivot detection + price clustering (DBSCAN-like)
2. Stop Loss — ATR-based trailing stop from most recent swing low
3. Bull/Bear Runs — EMA(20)/EMA(50) crossover zones
4. Moving Averages — 20 EMA, 50 EMA overlays
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

# ─── STOCK TICKERS (NSE/BSE) ───
STOCKS = [
    {"name": "Vodafone Idea",       "ticker": "IDEA.NS",        "display": "IDEA"},
    {"name": "Aurobindo Pharma",    "ticker": "AUROPHARMA.NS",  "display": "AUROPHARMA"},
    {"name": "NCC Limited",         "ticker": "NCC.NS",         "display": "NCC"},
    {"name": "HCC",                 "ticker": "HCC.NS",         "display": "HCC"},
    {"name": "Adani Green Energy",  "ticker": "ADANIGREEN.NS",  "display": "ADANIGREEN"},
    {"name": "Adani Power",         "ticker": "ADANIPOWER.NS",  "display": "ADANIPOWER"},
    {"name": "Waaree Energies",     "ticker": "WAAREEENER.NS",  "display": "WAAREEENER"},
    {"name": "Groww (Billionbrains)","ticker": "GROWW.NS",      "display": "GROWW"},
    {"name": "Digilogic Systems",   "ticker": "DIGILOGIC.NS",   "display": "DIGILOGIC"},
]

# ─── TECHNICAL ANALYSIS FUNCTIONS ───

def compute_ema(series, span):
    """Exponential Moving Average"""
    return series.ewm(span=span, adjust=False).mean()

def compute_atr(df, period=14):
    """Average True Range"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def find_fractals(df, window=5):
    """
    Detect swing highs and swing lows using fractal method.
    A swing high: high[i] is the highest in a window of 2*window+1 candles.
    A swing low: low[i] is the lowest in a window of 2*window+1 candles.
    """
    highs = df['High'].values
    lows = df['Low'].values
    n = len(highs)
    swing_highs = []
    swing_lows = []

    for i in range(window, n - window):
        # Swing high
        if highs[i] == max(highs[i - window:i + window + 1]):
            swing_highs.append((i, highs[i]))
        # Swing low
        if lows[i] == min(lows[i - window:i + window + 1]):
            swing_lows.append((i, lows[i]))

    return swing_highs, swing_lows

def cluster_levels(price_levels, tolerance_pct=0.015):
    """
    Cluster nearby price levels into support/resistance zones.
    Uses a simple greedy clustering with tolerance_pct of price.
    """
    if not price_levels:
        return []

    sorted_levels = sorted(price_levels)
    clusters = []
    current_cluster = [sorted_levels[0]]

    for price in sorted_levels[1:]:
        if abs(price - np.mean(current_cluster)) / np.mean(current_cluster) < tolerance_pct:
            current_cluster.append(price)
        else:
            clusters.append({
                'price': round(float(np.mean(current_cluster)), 2),
                'strength': len(current_cluster),  # more touches = stronger
            })
            current_cluster = [price]

    # Last cluster
    clusters.append({
        'price': round(float(np.mean(current_cluster)), 2),
        'strength': len(current_cluster),
    })

    # Only keep clusters with strength >= 2 (at least 2 touches)
    return [c for c in clusters if c['strength'] >= 2]

def compute_support_resistance(df):
    """
    Compute support and resistance levels using fractal pivots + clustering.
    Returns separate support and resistance lists.
    """
    swing_highs, swing_lows = find_fractals(df, window=5)

    # Also try with smaller window for more granularity
    sh2, sl2 = find_fractals(df, window=3)
    swing_highs.extend(sh2)
    swing_lows.extend(sl2)

    # Cluster high pivots → resistance
    high_prices = [h[1] for h in swing_highs]
    resistance = cluster_levels(high_prices)

    # Cluster low pivots → support
    low_prices = [l[1] for l in swing_lows]
    support = cluster_levels(low_prices)

    # Sort by strength (strongest first), take top levels
    resistance.sort(key=lambda x: x['strength'], reverse=True)
    support.sort(key=lambda x: x['strength'], reverse=True)

    current_price = float(df['Close'].iloc[-1])

    # Filter: resistance above current price, support below
    resistance = [r for r in resistance if r['price'] > current_price * 0.98][:4]
    support = [s for s in support if s['price'] < current_price * 1.02][:4]

    return support, resistance

def compute_stop_loss(df, atr_multiplier=2.0):
    """
    Compute stop loss using ATR-based method.
    Stop loss = Recent swing low - ATR * multiplier (for longs)
    Also provides a chandelier-style trailing stop.
    """
    atr = compute_atr(df, 14)
    current_atr = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0

    # Find most recent swing low (last 20 candles)
    _, swing_lows = find_fractals(df, window=3)
    recent_lows = [sl for sl in swing_lows if sl[0] >= len(df) - 25]

    if recent_lows:
        recent_swing_low = min(recent_lows, key=lambda x: x[1])[1]
    else:
        recent_swing_low = float(df['Low'].tail(20).min())

    # ATR-based stop loss
    atr_stop = round(recent_swing_low - (current_atr * 0.5), 2)

    # Chandelier stop (from highest high)
    highest_high = float(df['High'].tail(22).max())
    chandelier_stop = round(highest_high - (current_atr * atr_multiplier), 2)

    # Use the higher of the two (tighter stop)
    stop_loss = max(atr_stop, chandelier_stop)

    return {
        'stop_loss': round(float(stop_loss), 2),
        'atr_stop': round(float(atr_stop), 2),
        'chandelier_stop': round(float(chandelier_stop), 2),
        'current_atr': round(float(current_atr), 2),
        'method': 'ATR-based (max of swing-low and chandelier)',
    }

def compute_bull_bear_runs(df):
    """
    Identify bull and bear runs using EMA(20) / EMA(50) crossover.
    Bull run: EMA20 > EMA50
    Bear run: EMA20 < EMA50
    Returns list of zones with start/end dates and type.
    """
    ema20 = compute_ema(df['Close'], 20)
    ema50 = compute_ema(df['Close'], 50)

    runs = []
    current_run = None
    dates = df.index.tolist()

    for i in range(len(df)):
        if pd.isna(ema20.iloc[i]) or pd.isna(ema50.iloc[i]):
            continue

        is_bull = ema20.iloc[i] > ema50.iloc[i]
        run_type = 'bull' if is_bull else 'bear'

        if current_run is None:
            current_run = {
                'type': run_type,
                'start': dates[i].strftime('%Y-%m-%d'),
                'start_idx': i,
            }
        elif run_type != current_run['type']:
            current_run['end'] = dates[i - 1].strftime('%Y-%m-%d')
            current_run['end_idx'] = i - 1
            runs.append(current_run)
            current_run = {
                'type': run_type,
                'start': dates[i].strftime('%Y-%m-%d'),
                'start_idx': i,
            }

    # Close last run
    if current_run:
        current_run['end'] = dates[-1].strftime('%Y-%m-%d')
        current_run['end_idx'] = len(dates) - 1
        runs.append(current_run)

    # Clean up — remove idx fields
    for r in runs:
        r.pop('start_idx', None)
        r.pop('end_idx', None)

    return runs

def resample_to_weekly(df):
    """Resample daily OHLCV to weekly candles."""
    weekly = df.resample('W').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    }).dropna()
    return weekly

def df_to_candle_json(df):
    """Convert DataFrame to list of {time, open, high, low, close, volume} dicts."""
    records = []
    for date, row in df.iterrows():
        records.append({
            'time': date.strftime('%Y-%m-%d'),
            'open': round(float(row['Open']), 2),
            'high': round(float(row['High']), 2),
            'low': round(float(row['Low']), 2),
            'close': round(float(row['Close']), 2),
            'volume': int(row['Volume']) if not pd.isna(row['Volume']) else 0,
        })
    return records

def ema_to_json(df, span):
    """Compute EMA and return as line series data."""
    ema = compute_ema(df['Close'], span)
    records = []
    for date, val in ema.items():
        if not pd.isna(val):
            records.append({
                'time': date.strftime('%Y-%m-%d'),
                'value': round(float(val), 2),
            })
    return records

# ─── MAIN ───
def main():
    end_date = datetime(2026, 7, 30)
    start_date = end_date - timedelta(days=210)  # ~7 months to ensure 6 months of data after EMA warmup

    all_data = {}

    for stock in STOCKS:
        ticker = stock['ticker']
        display = stock['display']
        name = stock['name']
        print(f"Processing {name} ({ticker})...")

        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if df.empty:
                print(f"  WARNING: No data for {ticker}, skipping")
                continue

            # Flatten multi-index columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Ensure we have required columns
            required = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(c in df.columns for c in required):
                print(f"  WARNING: Missing columns for {ticker}: {df.columns.tolist()}")
                continue

            df = df[required].dropna()

            if len(df) < 30:
                print(f"  WARNING: Only {len(df)} rows for {ticker}, skipping")
                continue

            # Weekly resample
            weekly_df = resample_to_weekly(df)

            # ─── Technical Analysis ───
            support, resistance = compute_support_resistance(df)
            stop_loss_data = compute_stop_loss(df)
            bull_bear = compute_bull_bear_runs(df)
            ema20 = ema_to_json(df, 20)
            ema50 = ema_to_json(df, 50)
            weekly_ema20 = ema_to_json(weekly_df, 20)
            weekly_ema50 = ema_to_json(weekly_df, 50)

            # Weekly technical analysis
            w_support, w_resistance = compute_support_resistance(weekly_df) if len(weekly_df) >= 15 else (support, resistance)
            w_bull_bear = compute_bull_bear_runs(weekly_df) if len(weekly_df) >= 15 else bull_bear

            current_price = round(float(df['Close'].iloc[-1]), 2)
            day_change = round(float(df['Close'].iloc[-1] - df['Close'].iloc[-2]), 2) if len(df) >= 2 else 0
            day_change_pct = round((day_change / float(df['Close'].iloc[-2])) * 100, 2) if len(df) >= 2 else 0

            all_data[display] = {
                'name': name,
                'ticker': display,
                'current_price': current_price,
                'day_change': day_change,
                'day_change_pct': day_change_pct,
                'daily': {
                    'candles': df_to_candle_json(df),
                    'ema20': ema20,
                    'ema50': ema50,
                    'support': support,
                    'resistance': resistance,
                    'stop_loss': stop_loss_data,
                    'bull_bear_runs': bull_bear,
                },
                'weekly': {
                    'candles': df_to_candle_json(weekly_df),
                    'ema20': weekly_ema20,
                    'ema50': weekly_ema50,
                    'support': w_support,
                    'resistance': w_resistance,
                    'stop_loss': stop_loss_data,  # same stop loss
                    'bull_bear_runs': w_bull_bear,
                },
            }

            print(f"  OK: {len(df)} daily candles, {len(weekly_df)} weekly candles")
            print(f"  Support levels: {[s['price'] for s in support]}")
            print(f"  Resistance levels: {[r['price'] for r in resistance]}")
            print(f"  Stop loss: {stop_loss_data['stop_loss']}")
            print(f"  Bull/Bear runs: {len(bull_bear)} zones")

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

    # Save
    output_path = '/sessions/pensive-jolly-hamilton/mnt/outputs/stock_data.json'
    with open(output_path, 'w') as f:
        json.dump(all_data, f)

    print(f"\nDone. Saved {len(all_data)} stocks to {output_path}")
    print(f"File size: {os.path.getsize(output_path) / 1024:.1f} KB")

import os
if __name__ == '__main__':
    main()
