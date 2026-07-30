# Stock Watchlist Platform — Technical Design Document v2

**Version:** 2.0  
**Date:** 30 July 2026  
**Author:** Venkat  
**Status:** Draft  
**Change from v1:** Migrated from full-stack server architecture (FastAPI/Celery/PostgreSQL) to zero-cost serverless architecture (GitHub Actions + GitHub Pages + email delivery). No ongoing hosting costs.

---

## 1. Executive Summary

A fully automated, zero-cost stock analysis platform for 9 Indian stocks (NSE/BSE). Every morning before market open (9:15 AM IST), the system:

1. **Fetches** fresh OHLCV data from Yahoo Finance
2. **Runs** technical analysis algorithms (EMA, ATR, fractal pivots, support/resistance clustering, stop loss, bull/bear zones)
3. **Conducts** fundamental research (financials, sentiment, analyst consensus, risks, government investment tracker)
4. **Publishes** an interactive technical dashboard and a fundamental research report to a public website (GitHub Pages)
5. **Emails** the full report inline (HTML email with embedded charts) to the user

The entire system runs on free-tier infrastructure: GitHub Actions for compute/scheduling, GitHub Pages for hosting, SendGrid for email.

---

## 2. Architecture Overview

```
                    ┌──────────────────────────────────────┐
                    │       GitHub Actions (Cron)           │
                    │   Daily at 02:30 UTC (8:00 AM IST)   │
                    │   + 02:55 UTC (8:25 AM IST)          │
                    │                                       │
                    │  ┌────────────────────────────────┐   │
                    │  │  Ubuntu Runner (free tier)      │   │
                    │  │                                 │   │
                    │  │  1. pip install dependencies    │   │
                    │  │  2. python fetch_data.py        │   │
                    │  │  3. python ta_engine.py         │   │
                    │  │  4. python generate_dashboard.py│   │
                    │  │  5. python generate_report.py   │   │
                    │  │  6. python generate_email.py    │   │
                    │  │  7. python send_email.py        │   │
                    │  │  8. Deploy to gh-pages branch   │   │
                    │  └────────────────────────────────┘   │
                    └──────────┬──────────────┬─────────────┘
                               │              │
                ┌──────────────▼──┐    ┌──────▼──────────────┐
                │  GitHub Pages    │    │  SendGrid API       │
                │  (Static Site)   │    │  (Email Delivery)   │
                │                  │    │                      │
                │  /               │    │  Full HTML report    │
                │  /dashboard/     │    │  + chart images      │
                │  /report/        │    │  + dashboard link    │
                │  /archive/       │    │                      │
                └────────┬─────────┘    └──────────┬──────────┘
                         │                         │
                    ┌────▼─────────────────────────▼────┐
                    │          USER DEVICES              │
                    │  Chrome · Safari · Android · iOS   │
                    │  iPad · Desktop · Mobile           │
                    └───────────────────────────────────┘
```

### Why This Architecture

| Concern | Decision | Rationale |
|---------|----------|-----------|
| Cost | $0/month | GitHub Actions free tier (2000 min/month), GitHub Pages free, SendGrid free (100 emails/day) |
| Server management | None | No servers, databases, or containers to maintain |
| Reliability | High | GitHub's infrastructure handles uptime; if a run fails, retry on next cron trigger |
| Complexity | Low | Pure Python scripts, static HTML output, standard CI/CD |
| Scalability | Sufficient | 9 stocks × 2 API calls each = 18 requests; well within rate limits |

---

## 3. Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **Scheduler** | GitHub Actions cron | Free, reliable, no server needed |
| **Compute** | GitHub Actions Ubuntu runner | Python 3.11, 6 GB RAM, 2 CPU — plenty for TA |
| **Market Data** | Yahoo Finance v8 Chart API | Free, no API key, covers NSE/BSE |
| **TA Engine** | Python (numpy, pandas) | Native TA computation, no external service |
| **Chart Images** | Matplotlib + mplfinance | Static chart PNGs for email embedding |
| **Interactive Charts** | Lightweight Charts v4.1.1 (CDN) | TradingView open-source, fast, small |
| **Static Site** | Vanilla HTML/CSS/JS | No build step, fast, works everywhere |
| **Hosting** | GitHub Pages | Free, HTTPS, custom domain support |
| **Email** | SendGrid API (free tier) | 100 emails/day free, reliable delivery, HTML support |
| **Email Fallback** | Gmail SMTP (via `smtplib`) | Backup if SendGrid unavailable |

---

## 4. Stock Universe

| # | Company | Yahoo Ticker | Exchange | Sector |
|---|---------|-------------|----------|--------|
| 1 | Vodafone Idea | `IDEA.NS` | NSE | Telecom |
| 2 | Aurobindo Pharma | `AUROPHARMA.NS` | NSE | Pharma |
| 3 | NCC Limited | `NCC.NS` | NSE | Infrastructure |
| 4 | HCC | `HCC.NS` | NSE | Infrastructure |
| 5 | Adani Green Energy | `ADANIGREEN.NS` | NSE | Renewable Energy |
| 6 | Adani Power | `ADANIPOWER.NS` | NSE | Power |
| 7 | Waaree Energies | `WAAREEENER.NS` | NSE | Solar/Energy |
| 8 | Groww | `GROWW.NS` | NSE | Fintech |
| 9 | Digilogic Systems | `DIGILOGIC.BO` | BSE | IT/Micro-cap |

**Note:** DIGILOGIC trades on BSE only — use `.BO` suffix.

Stocks are configured in `config.py`. Adding/removing a stock is a one-line config change + commit.

---

## 5. Data Pipeline

### 5.1 Data Fetching (`scripts/fetch_data.py`)

**Source:** Yahoo Finance v8 Chart API (no authentication required)

**Endpoints:**

```
6-month daily OHLCV:
GET https://query1.finance.yahoo.com/v8/finance/chart/{TICKER}
    ?range=6mo&interval=1d&includePrePost=false

1-year daily (for 52-week high/low):
GET https://query1.finance.yahoo.com/v8/finance/chart/{TICKER}
    ?range=1y&interval=1d&includePrePost=false
```

**Response parsing:**

```python
data = response.json()["chart"]["result"][0]
timestamps = data["timestamp"]                          # Unix seconds
quotes = data["indicators"]["quote"][0]                 # {open, high, low, close, volume}
dates = [datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in timestamps]
```

**Rate limiting:** 200ms delay between requests. 18 total requests (9 stocks × 2 ranges) completes in ~4 seconds.

**Output:** `data/raw_ohlcv.json` — all 9 stocks' OHLCV data in one file.

```json
{
  "fetch_date": "2026-07-30",
  "stocks": {
    "IDEA": {
      "name": "Vodafone Idea",
      "ticker": "IDEA.NS",
      "ohlcv_6m": [
        {"date": "2026-01-30", "open": 9.96, "high": 11.38, "low": 9.86, "close": 11.17, "volume": 656772821},
        ...
      ],
      "week52_high": 15.34,
      "week52_low": 6.12
    },
    ...
  }
}
```

**Error handling:**
- HTTP errors: retry 3× with exponential backoff (1s, 2s, 4s)
- Ticker not found: log warning, skip stock, continue with others
- Weekend/holiday (no new data): still runs — last trading day's data is the latest candle

### 5.2 News & Fundamental Research (`scripts/fetch_fundamentals.py`)

**Sources (scraped server-side, no CORS issues):**

| Source | URL Pattern | Data Extracted |
|--------|-------------|----------------|
| Google News RSS | `https://news.google.com/rss/search?q={company}+stock+india` | Headlines, dates, links |
| Screener.in | `https://www.screener.in/company/{TICKER}/` | P/E, P/B, ROE, D/E, revenue growth |
| Moneycontrol | `https://www.moneycontrol.com/stocks/...` | Analyst ratings, target prices |
| Trendlyne | `https://trendlyne.com/equity/{TICKER}/` | Consensus, forecaster estimates |
| NSE/BSE filings | Corporate announcements page | Governance, regulatory news |
| Government sources | PIB, ministry announcements | Government investment tracker |

**Output:** `data/fundamentals.json`

---

## 6. Technical Analysis Engine — Full Algorithm Specification

All algorithms live in `scripts/ta_engine.py`. Each is a pure function: arrays in, results out. No side effects, fully testable.

### 6.1 EMA (Exponential Moving Average)

```python
def compute_ema(closes: list[float], span: int) -> list[float]:
    """
    Daily: span=20 (short), span=50 (long)
    Weekly: span=10 (short), span=20 (long)
    """
    k = 2.0 / (span + 1)
    ema = [closes[0]]
    for i in range(1, len(closes)):
        ema.append(closes[i] * k + ema[-1] * (1 - k))
    return ema
```

### 6.2 ATR (Average True Range)

```python
def compute_atr(highs, lows, closes, period=14) -> list[float | None]:
    """Returns list same length as input. First (period-1) values are None."""
    trs = [highs[0] - lows[0]]
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        trs.append(tr)
    
    atr = [None] * (period - 1)
    atr.append(sum(trs[:period]) / period)
    for i in range(period, len(trs)):
        atr.append((atr[-1] * (period - 1) + trs[i]) / period)  # Wilder smoothing
    return atr
```

### 6.3 Fractal Pivot Detection

```python
def find_fractals(highs, lows, window=5) -> tuple[list, list]:
    """
    Run with window=3 AND window=5, merge results.
    Swing high: high[i] == max(high[i-w .. i+w])
    Swing low:  low[i]  == min(low[i-w .. i+w])
    """
    swing_highs, swing_lows = [], []
    for i in range(window, len(highs) - window):
        if highs[i] == max(highs[i - window : i + window + 1]):
            swing_highs.append((i, highs[i]))
        if lows[i] == min(lows[i - window : i + window + 1]):
            swing_lows.append((i, lows[i]))
    return swing_highs, swing_lows
```

### 6.4 Price Level Clustering (Support/Resistance)

```python
def cluster_levels(prices: list[float], tolerance=0.015) -> list[dict]:
    """
    Greedy clustering: group prices within 1.5% of cluster mean.
    Returns [{price: float, strength: int}] where strength >= 2.
    """
    if not prices:
        return []
    prices_sorted = sorted(prices)
    clusters = []
    cluster = [prices_sorted[0]]
    
    for p in prices_sorted[1:]:
        if abs(p - (sum(cluster) / len(cluster))) / (sum(cluster) / len(cluster)) < tolerance:
            cluster.append(p)
        else:
            if len(cluster) >= 2:
                clusters.append({"price": round(sum(cluster) / len(cluster), 2), "strength": len(cluster)})
            cluster = [p]
    if len(cluster) >= 2:
        clusters.append({"price": round(sum(cluster) / len(cluster), 2), "strength": len(cluster)})
    
    return sorted(clusters, key=lambda x: -x["strength"])
```

**Post-processing:**
- Support = clusters from swing lows where `price < current_price * 1.02`. Top 4 by strength.
- Resistance = clusters from swing highs where `price > current_price * 0.98`. Top 4 by strength.

### 6.5 Stop Loss (ATR-Based with Fallback)

```python
def compute_stop_loss(highs, lows, closes, atr_values) -> dict:
    """
    Primary: max(swing_low - 0.5*ATR, highest_high_22 - 2*ATR)
    Fallback: if stop >= current_price → max(price - 1.5*ATR, min(lows[-30:]))
    """
    current = closes[-1]
    atr = atr_values[-1]
    
    # Recent swing low (last 25 candles)
    recent_lows = lows[-25:]
    swing_low = min(recent_lows)
    
    # ATR stop
    atr_stop = swing_low - 0.5 * atr
    
    # Chandelier stop
    highest_22 = max(highs[-22:])
    chandelier = highest_22 - 2.0 * atr
    
    stop = max(atr_stop, chandelier)
    method = "ATR-Chandelier"
    
    # Fallback for strongly downtrending stocks
    if stop >= current:
        stop = max(current - 1.5 * atr, min(lows[-30:]))
        method = "Fallback (downtrend)"
    
    return {
        "stop_loss": round(stop, 2),
        "atr": round(atr, 2),
        "risk_pct": round((current - stop) / current * 100, 1),
        "method": method
    }
```

### 6.6 Bull/Bear Zone Detection

```python
def compute_bull_bear_zones(closes, dates) -> list[dict]:
    """EMA(20) vs EMA(50) crossover. Returns zone transitions."""
    ema20 = compute_ema(closes, 20)
    ema50 = compute_ema(closes, 50)
    
    zones = []
    current_type = "bull" if ema20[0] > ema50[0] else "bear"
    current_start = dates[0]
    
    for i in range(1, len(closes)):
        new_type = "bull" if ema20[i] > ema50[i] else "bear"
        if new_type != current_type:
            zones.append({"type": current_type, "start": current_start, "end": dates[i - 1]})
            current_type = new_type
            current_start = dates[i]
    
    zones.append({"type": current_type, "start": current_start, "end": dates[-1]})
    return zones
```

### 6.7 Weekly Resampling

```python
def resample_weekly(daily_candles: list[dict]) -> list[dict]:
    """Group by ISO week (Monday start). Weekly EMAs use span=10 and span=20."""
    from itertools import groupby
    from datetime import datetime
    
    def week_key(c):
        d = datetime.strptime(c["date"], "%Y-%m-%d")
        iso = d.isocalendar()
        return (iso[0], iso[1])  # (year, week_number)
    
    weekly = []
    for _, group in groupby(daily_candles, key=week_key):
        candles = list(group)
        weekly.append({
            "date": candles[0]["date"],
            "open": candles[0]["open"],
            "high": max(c["high"] for c in candles),
            "low": min(c["low"] for c in candles),
            "close": candles[-1]["close"],
            "volume": sum(c["volume"] for c in candles),
        })
    return weekly
```

### 6.8 52-Week High/Low

```python
def compute_52w(ohlcv_1y: list[dict]) -> dict:
    """From 1-year data, compute max(high) and min(low)."""
    high = max(c["high"] for c in ohlcv_1y)
    low = min(c["low"] for c in ohlcv_1y)
    return {"week52_high": high, "week52_low": low}
```

---

## 7. Output Artifacts

The pipeline produces 5 artifacts per run:

| Artifact | File | Purpose |
|----------|------|---------|
| Raw data | `data/raw_ohlcv.json` | Cached OHLCV data (not deployed) |
| TA results | `data/ta_results.json` | Computed TA for all stocks (not deployed) |
| Dashboard HTML | `site/dashboard/index.html` | Interactive candlestick charts — deployed to GitHub Pages |
| Report HTML | `site/report/index.html` | Fundamental research report — deployed to GitHub Pages |
| Chart images | `site/assets/charts/*.png` | Static chart PNGs for email embedding |
| Email HTML | `data/email_body.html` | Inline-styled HTML sent via SendGrid (not deployed) |

---

## 8. Website (GitHub Pages)

### 8.1 URL Structure

Base URL: `https://{username}.github.io/stock-watchlist/`

| Path | Content |
|------|---------|
| `/` | Landing page — links to today's dashboard + report |
| `/dashboard/` | Interactive technical dashboard (Lightweight Charts) |
| `/report/` | Fundamental research report (styled HTML) |
| `/archive/` | Past reports index (auto-generated) |
| `/archive/2026-07-30/dashboard/` | Archived dashboard for specific date |
| `/archive/2026-07-30/report/` | Archived report for specific date |

### 8.2 Responsive Design

The site works on all devices. Layout adapts at these breakpoints:

| Breakpoint | Device | Dashboard Layout | Report Layout |
|-----------|--------|------------------|---------------|
| ≥ 1024px | Desktop/laptop | Chart + side info panel | 2-column cards |
| 768–1023px | iPad/tablet | Chart + panel stacked | 2-column cards |
| < 768px | Phone | Full-width chart, panel below, horizontal-scroll tabs | Single column |

**Key responsive rules:**
- Stock tabs: horizontal scroll with `-webkit-overflow-scrolling: touch` on mobile
- Chart: maintains 16:9 aspect ratio, min-height 300px on mobile
- Info panel: collapses to accordion sections on mobile
- Tables: horizontal scroll wrapper on narrow screens
- Touch targets: minimum 44×44px (Apple HIG)
- Font: system font stack, min 14px body text on mobile

### 8.3 Dashboard Page — Interactive Technical Charts

Self-contained HTML with all data embedded as inline JSON. No API calls at page load.

**Components:**

```
<DashboardPage>
  <Header>          "Stock Technical Dashboard — 30 Jul 2026"
  <StockTabs>       9 tabs, each showing ticker + daily change %
  <ControlBar>      [Daily] [Weekly] toggle + legend
  <ChartContainer>
    <Chart>          Lightweight Charts v4 candlestick
      CandlestickSeries    green (#3fb950) up, red (#f85149) down
      VolumeSeries         bottom 15%, colored by direction
      LineSeries           EMA20 (#58a6ff, 1px)
      LineSeries           EMA50 (#d2a8ff, 1px)
      PriceLine            Stop Loss (#f0883e, dashed)
      PriceLine[]          Support (#3fb950, dashed)
      PriceLine[]          Resistance (#f85149, dashed)
      PriceLine            52W High (#e3b341, dotted)
      PriceLine            52W Low (#a371f7, dotted)
      Markers[]            Bull/Bear zone transitions
    <InfoPanel>      280px sidebar (stacks below on mobile)
      Price + change + trend badge
      52W Range visual bar with position marker
      Stop Loss + ATR + risk %
      Support levels (price + touches + distance %)
      Resistance levels (price + touches + distance %)
      Recent trend zones (last 4)
  <Footer>           "Updated 30 Jul 2026, 08:30 IST"
```

**Color palette (dark theme):**

```css
--bg-primary:       #0a0e17;
--bg-card:          #161b22;
--border:           #21262d;
--text-primary:     #e1e4e8;
--text-secondary:   #8b949e;
--bullish:          #3fb950;
--bearish:          #f85149;
--stop-loss:        #f0883e;
--ema-short:        #58a6ff;
--ema-long:         #d2a8ff;
--w52-high:         #e3b341;
--w52-low:          #a371f7;
```

### 8.4 Report Page — Fundamental Research

Styled HTML report with the same data as the email, but with richer formatting (CSS animations, expandable sections, better typography).

**Structure per stock:**

```
<StockCard>
  <Header>       Company name, ticker, verdict badge (green/amber/red)
  <Section A>    Financial Performance
                   Revenue/profit growth, ROE, D/E, P/E, P/B
  <Section B>    Market Sentiment
                   Media mood, tailwinds, headwinds, governance
  <Section C>    Professional Consensus
                   Analyst ratings bar, target price range
  <Section D>    Risk Factors
                   Key risks, volatility vs Nifty 50
  <PlainEnglish> 2–3 sentence jargon-free summary
</StockCard>
```

Plus a Government Investment Tracker section at the bottom.

### 8.5 Landing Page

Simple, clean page linking to today's dashboard and report, plus the archive.

### 8.6 Archive System

Each day's output is copied to `/archive/{YYYY-MM-DD}/` before overwriting the latest. The archive index page is auto-generated from the directory listing. Keep 90 days of history (older archives are pruned by the GitHub Actions workflow to keep repo size manageable).

---

## 9. Email Specification

### 9.1 Email Delivery

| Property | Value |
|----------|-------|
| **Service** | SendGrid (free tier: 100 emails/day) |
| **Fallback** | Gmail SMTP via `smtplib` |
| **From** | `stockwatch@{your-domain}` or Gmail address |
| **To** | Configured in `config.py` |
| **Subject** | `📊 Stock Watchlist — {DD Mon YYYY} — {N} Bullish, {M} Bearish` |
| **Content-Type** | `text/html` (multipart/alternative with text fallback) |

### 9.2 Email HTML Design

Email HTML is heavily constrained — no JavaScript, limited CSS, table-based layout. The email must render correctly in Gmail, Apple Mail, Outlook, Yahoo Mail, and mobile email apps.

**Rules:**
- All CSS inline (no `<style>` block — Gmail strips it in non-AMP mode)
- Table-based layout (no flexbox, no grid)
- Max width: 600px (centered)
- Images: hosted on GitHub Pages (more reliable than base64 across clients)
- Font: system font stack (Arial fallback)
- Colors: same palette as website but on white/light background for email readability
- Dark mode: include `color-scheme: light dark` meta and `@media (prefers-color-scheme: dark)` overrides in a `<style>` block (Gmail ignores it but Apple Mail and iOS use it)

**Email Structure:**

```
┌──────────────────────────────────────────────────┐
│  HEADER                                          │
│  📊 Daily Stock Watchlist — 30 Jul 2026          │
│  View in browser: [link to report page]          │
├──────────────────────────────────────────────────┤
│  QUICK SCAN TABLE                                │
│  ┌────────┬────────┬──────────┬──────────┐       │
│  │ Stock  │ Price  │ Change   │ Verdict  │       │
│  ├────────┼────────┼──────────┼──────────┤       │
│  │ IDEA   │ ₹13.00 │ -0.38%  │ 🟡 Neut  │       │
│  │ AURO.. │ ₹1,540 │ +1.2%   │ 🟢 Pos   │       │
│  │ ...    │ ...    │ ...      │ ...      │       │
│  └────────┴────────┴──────────┴──────────┘       │
├──────────────────────────────────────────────────┤
│  TECHNICAL OVERVIEW CHART (static PNG image)     │
│  [Embedded candlestick mini-charts for 9 stocks] │
│  → View interactive dashboard: [link]            │
├──────────────────────────────────────────────────┤
│  PER-STOCK SECTIONS (×9)                         │
│  ┌──────────────────────────────────────────┐    │
│  │ 🏢 VODAFONE IDEA (IDEA.NS)     🟡 Neutral│    │
│  │                                          │    │
│  │ FINANCIALS                               │    │
│  │ Revenue growth: -2.1% YoY               │    │
│  │ ROE: -45.2% | D/E: 28.3 | P/E: N/A     │    │
│  │                                          │    │
│  │ SENTIMENT: Mixed — 5G spectrum hopes vs  │    │
│  │ continued subscriber losses              │    │
│  │                                          │    │
│  │ CONSENSUS: Buy 4 | Hold 8 | Sell 5      │    │
│  │ Target: ₹10–18 (median ₹14)             │    │
│  │                                          │    │
│  │ RISKS: High debt, negative cash flow,    │    │
│  │ competitive pressure from Jio/Airtel     │    │
│  │                                          │    │
│  │ TECHNICAL: Price ₹13.00 | SL ₹12.76     │    │
│  │ 52W: ₹6.12 — ₹15.34 (pos: 75%)        │    │
│  │ Support: ₹9.37 (3x) | Res: ₹14.85 (3x)│    │
│  │ Trend: 🐻 Bear since Jun 16             │    │
│  │                                          │    │
│  │ IN PLAIN ENGLISH: Vodafone Idea remains  │    │
│  │ a high-risk bet on India's 5G rollout... │    │
│  │                                          │    │
│  │ [Mini candlestick chart image]           │    │
│  └──────────────────────────────────────────┘    │
├──────────────────────────────────────────────────┤
│  GOVERNMENT INVESTMENT TRACKER                   │
│  Recent government-related investment news       │
│  affecting watchlist stocks...                   │
├──────────────────────────────────────────────────┤
│  FOOTER                                          │
│  Generated at 08:00 IST | View full dashboard    │
│  Manage subscription | GitHub                    │
└──────────────────────────────────────────────────┘
```

### 9.3 Chart Images for Email

Generated by `scripts/generate_email.py` using Matplotlib/mplfinance:

| Image | Dimensions | Content |
|-------|-----------|---------|
| `overview_grid.png` | 600×400px | 3×3 grid of mini candlestick charts, one per stock |
| `{ticker}_mini.png` | 560×200px | Per-stock candlestick with EMA20/50 and S/R lines |

Images are saved to `site/assets/charts/` and deployed to GitHub Pages. Email references them via absolute URLs: `https://{username}.github.io/stock-watchlist/assets/charts/overview_grid.png`

---

## 10. GitHub Actions Workflow

### 10.1 Schedule

Two workflows, staggered:

| Workflow | Cron (UTC) | IST Equivalent | Days | Purpose |
|----------|-----------|----------------|------|---------|
| `fundamental-report.yml` | `30 2 * * *` | 8:00 AM daily | Every day | Fetch fundamentals + generate report + email |
| `technical-dashboard.yml` | `55 2 * * 1-5` | 8:25 AM weekdays | Mon–Fri | Fetch OHLCV + run TA + generate dashboard |

Both deploy to GitHub Pages at the end.

### 10.2 Workflow File: `daily-update.yml` (combined)

```yaml
name: Daily Stock Update

on:
  schedule:
    - cron: '30 2 * * *'      # 8:00 AM IST daily (fundamentals + report)
    - cron: '55 2 * * 1-5'    # 8:25 AM IST weekdays (TA dashboard)
  workflow_dispatch:            # Manual trigger button

permissions:
  contents: write              # Push to gh-pages branch
  pages: write

jobs:
  update:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Determine job type
        id: job-type
        run: |
          HOUR=$(date -u +%H)
          MIN=$(date -u +%M)
          DOW=$(date -u +%u)
          if [ "$GITHUB_EVENT_NAME" = "workflow_dispatch" ]; then
            echo "type=full" >> $GITHUB_OUTPUT
          elif [ "$HOUR" = "02" ] && [ "$MIN" -lt "50" ]; then
            echo "type=fundamental" >> $GITHUB_OUTPUT
          else
            echo "type=technical" >> $GITHUB_OUTPUT
          fi
      
      - name: Fetch market data
        run: python scripts/fetch_data.py
      
      - name: Run technical analysis
        if: steps.job-type.outputs.type == 'technical' || steps.job-type.outputs.type == 'full'
        run: python scripts/ta_engine.py
      
      - name: Fetch fundamental research
        if: steps.job-type.outputs.type == 'fundamental' || steps.job-type.outputs.type == 'full'
        run: python scripts/fetch_fundamentals.py
      
      - name: Generate dashboard
        if: steps.job-type.outputs.type == 'technical' || steps.job-type.outputs.type == 'full'
        run: python scripts/generate_dashboard.py
      
      - name: Generate report
        if: steps.job-type.outputs.type == 'fundamental' || steps.job-type.outputs.type == 'full'
        run: python scripts/generate_report.py
      
      - name: Generate email + chart images
        run: python scripts/generate_email.py
      
      - name: Send email
        run: python scripts/send_email.py
        env:
          SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
          EMAIL_TO: ${{ secrets.EMAIL_TO }}
          SITE_URL: ${{ vars.SITE_URL }}
      
      - name: Archive today's output
        run: |
          DATE=$(date +%Y-%m-%d)
          mkdir -p site/archive/$DATE
          cp -r site/dashboard site/archive/$DATE/ 2>/dev/null || true
          cp -r site/report site/archive/$DATE/ 2>/dev/null || true
      
      - name: Prune old archives (keep 90 days)
        run: |
          cd site/archive
          CUTOFF=$(date -d '90 days ago' +%Y-%m-%d 2>/dev/null || date -v-90d +%Y-%m-%d)
          for dir in 20*; do
            if [ "$dir" \< "$CUTOFF" ]; then
              rm -rf "$dir"
            fi
          done
      
      - name: Generate archive index
        run: python scripts/generate_archive_index.py
      
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./site
          force_orphan: false
```

### 10.3 Repository Secrets

| Secret | Description | How to Set |
|--------|------------|------------|
| `SENDGRID_API_KEY` | SendGrid API key for email | Free at sendgrid.com → Settings → API Keys |
| `EMAIL_TO` | Recipient email address | Your email |
| `SITE_URL` | GitHub Pages base URL | `https://{user}.github.io/stock-watchlist` |

### 10.4 GitHub Pages Setup

1. Go to repo Settings → Pages
2. Source: "Deploy from a branch"
3. Branch: `gh-pages` / `/ (root)`
4. Save

Custom domain (optional): add a `CNAME` file to `site/` with your domain.

---

## 11. Project Structure

```
stock-watchlist/
├── .github/
│   └── workflows/
│       └── daily-update.yml           # GitHub Actions cron workflow
├── scripts/
│   ├── config.py                      # Stock list, email settings, constants
│   ├── fetch_data.py                  # Yahoo Finance OHLCV fetcher
│   ├── fetch_fundamentals.py          # News/sentiment/analyst scraper
│   ├── ta_engine.py                   # All TA algorithms (§6)
│   ├── generate_dashboard.py          # Interactive HTML dashboard builder
│   ├── generate_report.py             # Fundamental report HTML builder
│   ├── generate_email.py              # Email-safe HTML + chart images
│   ├── generate_archive_index.py      # Archive page auto-generator
│   └── send_email.py                  # SendGrid/SMTP email sender
├── site/
│   ├── index.html                     # Landing page
│   ├── dashboard/
│   │   └── index.html                 # ← generated by CI (gitignored)
│   ├── report/
│   │   └── index.html                 # ← generated by CI (gitignored)
│   ├── archive/
│   │   └── index.html                 # ← generated by CI
│   ├── assets/
│   │   ├── charts/                    # ← generated chart PNGs (gitignored)
│   │   └── favicon.png
│   └── css/
│       └── styles.css                 # Shared styles for landing + archive
├── data/                              # ← generated data files (gitignored)
│   └── .gitkeep
├── tests/
│   ├── test_ta_engine.py              # Unit tests for all TA algorithms
│   ├── test_fetch_data.py             # Mock API response tests
│   └── test_generate_email.py         # Email HTML validation
├── .gitignore
├── requirements.txt
├── LICENSE
└── README.md
```

**`.gitignore`:**
```
data/*.json
site/dashboard/index.html
site/report/index.html
site/assets/charts/*.png
__pycache__/
*.pyc
.env
```

---

## 12. Configuration

All settings in `scripts/config.py`:

```python
STOCKS = [
    {"ticker": "IDEA.NS",         "key": "IDEA",        "name": "Vodafone Idea",      "sector": "Telecom"},
    {"ticker": "AUROPHARMA.NS",   "key": "AUROPHARMA",  "name": "Aurobindo Pharma",   "sector": "Pharma"},
    {"ticker": "NCC.NS",          "key": "NCC",         "name": "NCC Limited",         "sector": "Infrastructure"},
    {"ticker": "HCC.NS",          "key": "HCC",         "name": "HCC",                 "sector": "Infrastructure"},
    {"ticker": "ADANIGREEN.NS",   "key": "ADANIGREEN",  "name": "Adani Green Energy",  "sector": "Renewable Energy"},
    {"ticker": "ADANIPOWER.NS",   "key": "ADANIPOWER",  "name": "Adani Power",         "sector": "Power"},
    {"ticker": "WAAREEENER.NS",   "key": "WAAREEENER",  "name": "Waaree Energies",     "sector": "Solar/Energy"},
    {"ticker": "GROWW.NS",        "key": "GROWW",       "name": "Groww",               "sector": "Fintech"},
    {"ticker": "DIGILOGIC.BO",    "key": "DIGILOGIC",   "name": "Digilogic Systems",   "sector": "IT/Micro-cap"},
]

# Yahoo Finance API
YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
FETCH_DELAY = 0.2  # seconds between requests

# TA parameters
EMA_SHORT = 20
EMA_LONG = 50
EMA_WEEKLY_SHORT = 10
EMA_WEEKLY_LONG = 20
ATR_PERIOD = 14
FRACTAL_WINDOWS = [3, 5]
CLUSTER_TOLERANCE = 0.015
CLUSTER_MIN_TOUCHES = 2
STOP_LOSS_ATR_MULT = 0.5
CHANDELIER_MULT = 2.0
FALLBACK_ATR_MULT = 1.5

# Email
EMAIL_FROM = "Stock Watchlist <noreply@stockwatch.dev>"
EMAIL_SUBJECT_TEMPLATE = "📊 Stock Watchlist — {date} — {summary}"

# Paths (relative to repo root)
DATA_DIR = "data"
SITE_DIR = "site"
CHART_DIR = "site/assets/charts"
```

---

## 13. Error Handling

| Scenario | Response |
|----------|----------|
| Yahoo Finance API down | Retry 3× (1s, 2s, 4s backoff). If all fail, use last successful data from previous commit. Log warning. |
| Single stock fetch fails | Skip that stock. Email and dashboard show "Data unavailable" for it. Others continue normally. |
| Market holiday (no trading) | Pipeline runs but latest candle is previous trading day. No error. |
| SendGrid API error | Fall back to Gmail SMTP. If both fail, log error — data is still deployed to GitHub Pages. |
| GitHub Actions timeout (15 min) | Very unlikely for 9 stocks. If hit, split into two workflows. |
| GitHub Pages deploy fail | Retry via `workflow_dispatch` manual trigger. Previous deployment stays live. |
| Repo size growing (archives) | 90-day auto-prune keeps it under 500 MB. Each day ≈ 300 KB. |

---

## 14. Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_ta_engine.py -v

# Run with coverage
pytest tests/ --cov=scripts --cov-report=html
```

**Key test cases:**

| Test | Validates |
|------|-----------|
| `test_ema_constant_series` | EMA of constant values equals that constant |
| `test_ema_convergence` | EMA converges toward recent prices |
| `test_atr_single_candle` | ATR of one candle = high - low |
| `test_fractal_v_shape` | Fractal detects exact bottom of V pattern |
| `test_cluster_merge` | Prices within 1.5% merge; beyond 1.5% don't |
| `test_stop_loss_normal` | Stop loss < current price for uptrending stock |
| `test_stop_loss_fallback` | Fallback triggers for downtrending stock |
| `test_weekly_resample` | 5 daily candles → 1 weekly candle with correct OHLCV |
| `test_bull_bear_zones` | Golden cross produces bull zone, death cross produces bear |
| `test_email_html_valid` | Generated email HTML passes W3C validation (no JS, tables only) |
| `test_email_images_reachable` | All image URLs in email exist in site/assets/charts/ |

---

## 15. Setup Guide (for developer)

### Step 1: Fork & Clone

```bash
git clone https://github.com/{your-username}/stock-watchlist.git
cd stock-watchlist
pip install -r requirements.txt
```

### Step 2: Local Test Run

```bash
python scripts/fetch_data.py           # Fetches fresh data → data/
python scripts/ta_engine.py            # Runs TA → data/ta_results.json
python scripts/generate_dashboard.py   # Builds → site/dashboard/index.html
python scripts/generate_report.py      # Builds → site/report/index.html
python scripts/generate_email.py       # Builds → data/email_body.html + chart PNGs

# Open in browser
open site/dashboard/index.html
open site/report/index.html
```

### Step 3: Configure Secrets

In GitHub → repo Settings → Secrets and variables → Actions:

1. `SENDGRID_API_KEY` — from sendgrid.com (free account)
2. `EMAIL_TO` — your email address
3. Set variable `SITE_URL` — `https://{user}.github.io/stock-watchlist`

### Step 4: Enable GitHub Pages

Settings → Pages → Source: "Deploy from a branch" → Branch: `gh-pages` → Save

### Step 5: First Deploy

Either push to `main` (triggers on push if configured) or click "Run workflow" on the Actions tab.

### Step 6: Verify

- Check `https://{user}.github.io/stock-watchlist/` loads
- Check email arrives
- Check Actions tab for green ✓

---

## 16. Cost Analysis

| Service | Free Tier | Usage | Monthly Cost |
|---------|----------|-------|-------------|
| GitHub Actions | 2,000 min/month | ~5 min/run × 30 runs = 150 min | **$0** |
| GitHub Pages | 1 GB storage, 100 GB bandwidth | ~50 MB storage, ~1 GB bandwidth | **$0** |
| SendGrid | 100 emails/day | 1 email/day | **$0** |
| Yahoo Finance API | Unlimited (no key) | ~18 requests/day | **$0** |
| **Total** | | | **$0/month** |

---

## 17. Future Enhancements

- **Multiple recipients:** Add email list to config; SendGrid supports batch sending
- **Telegram/WhatsApp bot:** Send morning summary to messaging apps
- **Custom domain:** Point your domain to GitHub Pages (free with CNAME)
- **Intraday updates:** Add a second workflow run at 3:00 PM IST for mid-day check
- **PWA (Progressive Web App):** Add manifest.json + service worker for "Add to Home Screen" on mobile
- **Dark/light mode toggle:** Website supports both; email auto-detects via `prefers-color-scheme`
- **Watchlist management UI:** Simple GitHub-hosted form that creates a PR to modify `config.py`
- **Backtesting:** Historical accuracy tracking of stop loss and S/R predictions
- **Additional indicators:** RSI, MACD, Bollinger Bands as toggleable overlays
