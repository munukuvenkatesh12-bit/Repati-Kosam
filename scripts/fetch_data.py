"""
Fetch OHLCV data from Yahoo Finance for all stocks.
Outputs: data/raw_ohlcv.json
"""
import json
import time
import sys
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from config import STOCKS, YAHOO_BASE, FETCH_DELAY, FETCH_RETRIES, FETCH_BACKOFF, DATA_DIR

IST = timezone(timedelta(hours=5, minutes=30))


def fetch_yahoo(ticker: str, range_str: str, interval: str = "1d") -> dict | None:
    """Fetch OHLCV from Yahoo Finance v8 Chart API with retries."""
    url = f"{YAHOO_BASE}/{ticker}?range={range_str}&interval={interval}&includePrePost=false"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; StockWatchlist/2.0)"}

    for attempt in range(FETCH_RETRIES):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            result = data.get("chart", {}).get("result")
            if not result:
                print(f"  ⚠ No data in response for {ticker} ({range_str})")
                return None
            return result[0]
        except (HTTPError, URLError, Exception) as e:
            wait = FETCH_BACKOFF[attempt] if attempt < len(FETCH_BACKOFF) else 4
            print(f"  ⚠ Attempt {attempt + 1}/{FETCH_RETRIES} failed for {ticker}: {e}")
            if attempt < FETCH_RETRIES - 1:
                time.sleep(wait)
    return None


def parse_ohlcv(result: dict) -> list[dict]:
    """Parse Yahoo Finance result into list of OHLCV dicts."""
    timestamps = result.get("timestamp", [])
    quotes = result.get("indicators", {}).get("quote", [{}])[0]

    candles = []
    for i, ts in enumerate(timestamps):
        o = quotes.get("open", [None])[i]
        h = quotes.get("high", [None])[i]
        l = quotes.get("low", [None])[i]
        c = quotes.get("close", [None])[i]
        v = quotes.get("volume", [0])[i]
        # Skip candles with None values (market holidays)
        if any(x is None for x in [o, h, l, c]):
            continue
        dt = datetime.fromtimestamp(ts, tz=IST)
        candles.append({
            "date": dt.strftime("%Y-%m-%d"),
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(c, 2),
            "volume": int(v or 0),
        })
    return candles


def main():
    print(f"🔄 Fetching market data at {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}")
    output = {
        "fetch_date": datetime.now(IST).strftime("%Y-%m-%d"),
        "fetch_time": datetime.now(IST).strftime("%H:%M IST"),
        "stocks": {},
    }

    success_count = 0
    for stock in STOCKS:
        ticker = stock["ticker"]
        key = stock["key"]
        print(f"\n📈 {key} ({ticker})")

        # 6-month daily OHLCV
        print(f"  Fetching 6-month data...")
        result_6m = fetch_yahoo(ticker, "6mo")
        time.sleep(FETCH_DELAY)

        # 1-year daily (for 52-week high/low)
        print(f"  Fetching 1-year data...")
        result_1y = fetch_yahoo(ticker, "1y")
        time.sleep(FETCH_DELAY)

        if not result_6m:
            print(f"  ❌ Failed to fetch 6-month data for {key}")
            output["stocks"][key] = {"error": "Data unavailable", "name": stock["name"], "ticker": ticker}
            continue

        candles_6m = parse_ohlcv(result_6m)
        if not candles_6m:
            print(f"  ❌ No valid candles for {key}")
            output["stocks"][key] = {"error": "No valid candles", "name": stock["name"], "ticker": ticker}
            continue

        # 52-week high/low
        w52_high, w52_low = None, None
        if result_1y:
            candles_1y = parse_ohlcv(result_1y)
            if candles_1y:
                w52_high = max(c["high"] for c in candles_1y)
                w52_low = min(c["low"] for c in candles_1y)

        latest = candles_6m[-1]
        prev = candles_6m[-2] if len(candles_6m) > 1 else candles_6m[-1]
        change = round(latest["close"] - prev["close"], 2)
        change_pct = round(change / prev["close"] * 100, 2) if prev["close"] else 0

        output["stocks"][key] = {
            "name": stock["name"],
            "ticker": ticker,
            "sector": stock["sector"],
            "current_price": latest["close"],
            "day_change": change,
            "day_change_pct": change_pct,
            "week52_high": round(w52_high, 2) if w52_high else None,
            "week52_low": round(w52_low, 2) if w52_low else None,
            "ohlcv_6m": candles_6m,
        }
        success_count += 1
        print(f"  ✅ {len(candles_6m)} candles | Price: ₹{latest['close']} ({change_pct:+.1f}%)")

    # Write output
    out_path = DATA_DIR / "raw_ohlcv.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Fetched {success_count}/{len(STOCKS)} stocks → {out_path}")

    if success_count == 0:
        print("❌ No stocks fetched successfully. Exiting with error.")
        sys.exit(1)


if __name__ == "__main__":
    main()
