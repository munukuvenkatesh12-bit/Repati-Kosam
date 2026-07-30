"""
Technical Analysis Engine — All algorithms.
Input:  data/raw_ohlcv.json
Output: data/ta_results.json

Algorithms: EMA, ATR, Fractal Pivots, S/R Clustering, Stop Loss, Bull/Bear Zones, Weekly Resampling, 52W Range.
"""
import json
import sys
from itertools import groupby
from datetime import datetime

from config import (
    DATA_DIR, EMA_SHORT, EMA_LONG, EMA_WEEKLY_SHORT, EMA_WEEKLY_LONG,
    ATR_PERIOD, FRACTAL_WINDOWS, CLUSTER_TOLERANCE, CLUSTER_MIN_TOUCHES,
    STOP_LOSS_ATR_MULT, CHANDELIER_MULT, FALLBACK_ATR_MULT,
)


# ──────────────────────────────────────────────
# Core Indicators
# ──────────────────────────────────────────────

def compute_ema(closes: list[float], span: int) -> list[float]:
    """Exponential Moving Average."""
    k = 2.0 / (span + 1)
    ema = [closes[0]]
    for i in range(1, len(closes)):
        ema.append(closes[i] * k + ema[-1] * (1 - k))
    return ema


def compute_atr(highs: list[float], lows: list[float], closes: list[float],
                period: int = ATR_PERIOD) -> list[float | None]:
    """Average True Range (Wilder smoothing)."""
    trs = [highs[0] - lows[0]]
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)

    atr = [None] * (period - 1)
    atr.append(sum(trs[:period]) / period)
    for i in range(period, len(trs)):
        atr.append((atr[-1] * (period - 1) + trs[i]) / period)
    return atr


# ──────────────────────────────────────────────
# Support / Resistance
# ──────────────────────────────────────────────

def find_fractals(highs: list[float], lows: list[float], window: int = 5):
    """Find swing highs and swing lows using a fractal window."""
    swing_highs, swing_lows = [], []
    for i in range(window, len(highs) - window):
        region_h = highs[i - window: i + window + 1]
        region_l = lows[i - window: i + window + 1]
        if highs[i] == max(region_h):
            swing_highs.append((i, highs[i]))
        if lows[i] == min(region_l):
            swing_lows.append((i, lows[i]))
    return swing_highs, swing_lows


def cluster_levels(prices: list[float], tolerance: float = CLUSTER_TOLERANCE,
                   min_touches: int = CLUSTER_MIN_TOUCHES) -> list[dict]:
    """Greedy price clustering. Returns [{price, strength}]."""
    if not prices:
        return []
    prices_sorted = sorted(prices)
    clusters = []
    cluster = [prices_sorted[0]]

    for p in prices_sorted[1:]:
        mean = sum(cluster) / len(cluster)
        if abs(p - mean) / mean < tolerance:
            cluster.append(p)
        else:
            if len(cluster) >= min_touches:
                clusters.append({
                    "price": round(sum(cluster) / len(cluster), 2),
                    "strength": len(cluster),
                })
            cluster = [p]
    if len(cluster) >= min_touches:
        clusters.append({
            "price": round(sum(cluster) / len(cluster), 2),
            "strength": len(cluster),
        })

    return sorted(clusters, key=lambda x: -x["strength"])


def compute_support_resistance(highs, lows, current_price):
    """Full pipeline: fractals (window 3+5) → clustering → split into S/R."""
    all_swing_highs, all_swing_lows = [], []
    for w in FRACTAL_WINDOWS:
        sh, sl = find_fractals(highs, lows, w)
        all_swing_highs.extend(sh)
        all_swing_lows.extend(sl)

    # Deduplicate by index
    seen_h, seen_l = set(), set()
    unique_highs, unique_lows = [], []
    for idx, price in all_swing_highs:
        if idx not in seen_h:
            seen_h.add(idx)
            unique_highs.append(price)
    for idx, price in all_swing_lows:
        if idx not in seen_l:
            seen_l.add(idx)
            unique_lows.append(price)

    resistance_raw = cluster_levels(unique_highs)
    support_raw = cluster_levels(unique_lows)

    # Filter relative to current price
    resistance = [r for r in resistance_raw if r["price"] > current_price * 0.98][:4]
    support = [s for s in support_raw if s["price"] < current_price * 1.02][:4]

    return support, resistance


# ──────────────────────────────────────────────
# Stop Loss
# ──────────────────────────────────────────────

def compute_stop_loss(highs, lows, closes, atr_values) -> dict:
    """ATR-based stop loss with chandelier and fallback."""
    current = closes[-1]
    atr = atr_values[-1]
    if atr is None or atr == 0:
        return {"stop_loss": round(current * 0.95, 2), "atr": 0, "risk_pct": 5.0, "method": "Fixed 5%"}

    # Recent swing low
    swing_low = min(lows[-25:]) if len(lows) >= 25 else min(lows)
    atr_stop = swing_low - STOP_LOSS_ATR_MULT * atr

    # Chandelier
    lookback = min(22, len(highs))
    highest = max(highs[-lookback:])
    chandelier = highest - CHANDELIER_MULT * atr

    stop = max(atr_stop, chandelier)
    method = "ATR-Chandelier"

    # Fallback for downtrending stocks
    if stop >= current:
        fallback_low = min(lows[-30:]) if len(lows) >= 30 else min(lows)
        stop = max(current - FALLBACK_ATR_MULT * atr, fallback_low)
        method = "Fallback (downtrend)"

    risk_pct = round((current - stop) / current * 100, 1) if current > 0 else 0
    return {
        "stop_loss": round(stop, 2),
        "atr": round(atr, 2),
        "risk_pct": max(risk_pct, 0.1),
        "method": method,
    }


# ──────────────────────────────────────────────
# Bull / Bear Zones
# ──────────────────────────────────────────────

def compute_bull_bear_zones(closes, dates, short=EMA_SHORT, long=EMA_LONG) -> list[dict]:
    """EMA crossover zones."""
    ema_s = compute_ema(closes, short)
    ema_l = compute_ema(closes, long)

    zones = []
    current_type = "bull" if ema_s[0] >= ema_l[0] else "bear"
    current_start = dates[0]

    for i in range(1, len(closes)):
        new_type = "bull" if ema_s[i] >= ema_l[i] else "bear"
        if new_type != current_type:
            zones.append({"type": current_type, "start": current_start, "end": dates[i - 1]})
            current_type = new_type
            current_start = dates[i]

    zones.append({"type": current_type, "start": current_start, "end": dates[-1]})
    return zones


# ──────────────────────────────────────────────
# Weekly Resampling
# ──────────────────────────────────────────────

def resample_weekly(candles: list[dict]) -> list[dict]:
    """Group daily candles by ISO week."""
    def week_key(c):
        d = datetime.strptime(c["date"], "%Y-%m-%d")
        iso = d.isocalendar()
        return (iso[0], iso[1])

    weekly = []
    for _, group in groupby(candles, key=week_key):
        cs = list(group)
        weekly.append({
            "date": cs[0]["date"],
            "open": cs[0]["open"],
            "high": round(max(c["high"] for c in cs), 2),
            "low": round(min(c["low"] for c in cs), 2),
            "close": cs[-1]["close"],
            "volume": sum(c["volume"] for c in cs),
        })
    return weekly


# ──────────────────────────────────────────────
# Full Analysis Pipeline (per stock)
# ──────────────────────────────────────────────

def analyze_stock(stock_data: dict) -> dict:
    """Run all TA algorithms on one stock. Returns full result dict."""
    candles = stock_data["ohlcv_6m"]
    dates = [c["date"] for c in candles]
    opens = [c["open"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]
    volumes = [c["volume"] for c in candles]
    current = closes[-1]

    # ── Daily TA ──
    ema20 = compute_ema(closes, EMA_SHORT)
    ema50 = compute_ema(closes, EMA_LONG)
    atr_vals = compute_atr(highs, lows, closes, ATR_PERIOD)
    support, resistance = compute_support_resistance(highs, lows, current)
    stop_loss = compute_stop_loss(highs, lows, closes, atr_vals)
    bull_bear = compute_bull_bear_zones(closes, dates)

    daily = {
        "candles": candles,
        "ema_short": [{"time": dates[i], "value": round(ema20[i], 2)} for i in range(len(dates))],
        "ema_long": [{"time": dates[i], "value": round(ema50[i], 2)} for i in range(len(dates))],
        "support": support,
        "resistance": resistance,
        "stop_loss": stop_loss,
        "bull_bear_runs": bull_bear,
    }

    # ── Weekly TA ──
    weekly_candles = resample_weekly(candles)
    if len(weekly_candles) >= 2:
        w_dates = [c["date"] for c in weekly_candles]
        w_closes = [c["close"] for c in weekly_candles]
        w_highs = [c["high"] for c in weekly_candles]
        w_lows = [c["low"] for c in weekly_candles]
        w_ema10 = compute_ema(w_closes, EMA_WEEKLY_SHORT)
        w_ema20 = compute_ema(w_closes, EMA_WEEKLY_LONG)
        w_atr = compute_atr(w_highs, w_lows, w_closes, ATR_PERIOD)
        w_support, w_resistance = compute_support_resistance(w_highs, w_lows, current)
        w_stop = compute_stop_loss(w_highs, w_lows, w_closes, w_atr)
        w_zones = compute_bull_bear_zones(w_closes, w_dates, EMA_WEEKLY_SHORT, EMA_WEEKLY_LONG)

        weekly = {
            "candles": weekly_candles,
            "ema_short": [{"time": w_dates[i], "value": round(w_ema10[i], 2)} for i in range(len(w_dates))],
            "ema_long": [{"time": w_dates[i], "value": round(w_ema20[i], 2)} for i in range(len(w_dates))],
            "support": w_support,
            "resistance": w_resistance,
            "stop_loss": w_stop,
            "bull_bear_runs": w_zones,
        }
    else:
        weekly = {"candles": weekly_candles, "ema_short": [], "ema_long": [],
                  "support": [], "resistance": [], "stop_loss": {}, "bull_bear_runs": []}

    return {
        "name": stock_data["name"],
        "ticker": stock_data["ticker"],
        "sector": stock_data.get("sector", ""),
        "current_price": current,
        "day_change": stock_data.get("day_change", 0),
        "day_change_pct": stock_data.get("day_change_pct", 0),
        "week52_high": stock_data.get("week52_high"),
        "week52_low": stock_data.get("week52_low"),
        "trend": bull_bear[-1]["type"] if bull_bear else "unknown",
        "daily": daily,
        "weekly": weekly,
    }


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    raw_path = DATA_DIR / "raw_ohlcv.json"
    if not raw_path.exists():
        print("❌ data/raw_ohlcv.json not found. Run fetch_data.py first.")
        sys.exit(1)

    with open(raw_path) as f:
        raw = json.load(f)

    print(f"🔧 Running technical analysis on {len(raw['stocks'])} stocks...")
    results = {"date": raw["fetch_date"], "stocks": {}}

    for key, stock_data in raw["stocks"].items():
        if "error" in stock_data:
            print(f"  ⚠ Skipping {key}: {stock_data['error']}")
            results["stocks"][key] = {"error": stock_data["error"], "name": stock_data.get("name", key)}
            continue

        candles = stock_data.get("ohlcv_6m", [])
        if len(candles) < 30:
            print(f"  ⚠ Skipping {key}: only {len(candles)} candles (need ≥30)")
            results["stocks"][key] = {"error": "Insufficient data", "name": stock_data.get("name", key)}
            continue

        print(f"  📊 {key}...", end=" ")
        result = analyze_stock(stock_data)
        results["stocks"][key] = result
        trend_emoji = "🐂" if result["trend"] == "bull" else "🐻"
        print(f"{trend_emoji} {result['trend']} | SL: ₹{result['daily']['stop_loss']['stop_loss']} "
              f"| S: {len(result['daily']['support'])} R: {len(result['daily']['resistance'])}")

    out_path = DATA_DIR / "ta_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ TA results → {out_path}")


if __name__ == "__main__":
    main()
