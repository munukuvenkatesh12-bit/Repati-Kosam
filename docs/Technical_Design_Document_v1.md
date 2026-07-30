# Stock Watchlist Platform — Technical Design Document

**Version:** 1.0  
**Date:** 30 July 2026  
**Author:** Venkat  
**Status:** Draft  

---

## 1. Executive Summary

This document describes a full-stack web platform that automates two daily pre-market workflows for a portfolio of 9 Indian stocks (NSE/BSE listed):

1. **Fundamental Research Report** — A PDF report covering financials, sentiment, analyst consensus, risks, and a government investment tracker, generated daily at 8:00 AM IST.
2. **Technical Analysis Dashboard** — An interactive candlestick charting dashboard with algorithmically computed support/resistance, stop loss, bull/bear zones, 52-week range, and EMA overlays, regenerated daily at 8:30 AM IST (weekdays).

Both are delivered before NSE/BSE market open (9:15 AM IST).

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                         │
│  ┌──────────────┐  ┌──────────────────────────────────────────┐ │
│  │  PDF Viewer   │  │  Technical Dashboard (SPA)               │ │
│  │  (Download)   │  │  - Lightweight Charts (candlestick)      │ │
│  │              │  │  - Stock tabs, Daily/Weekly toggle        │ │
│  │              │  │  - Info panel (S/R, SL, 52W, trends)     │ │
│  └──────────────┘  └──────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
┌────────────────────────────▼────────────────────────────────────┐
│                     API GATEWAY / WEB SERVER                    │
│                     (FastAPI / Python 3.11+)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐  │
│  │ /api/report  │  │ /api/dashboard│ │ /api/stocks            │  │
│  │ GET latest   │  │ GET latest    │ │ GET list, GET {ticker} │  │
│  │ GET history  │  │ GET {ticker}  │ │ PUT (admin: add/remove)│  │
│  └─────────────┘  └─────────────┘  └────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      BACKEND SERVICES                           │
│                                                                 │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐ │
│  │  SCHEDULER SERVICE   │  │  DATA PIPELINE SERVICE           │ │
│  │  (APScheduler /      │  │                                  │ │
│  │   Celery Beat)       │  │  ┌────────────┐ ┌─────────────┐ │ │
│  │                      │  │  │ Market Data │ │ News/Sent.  │ │ │
│  │  Job 1: 8:00 AM IST  │  │  │ Fetcher    │ │ Fetcher     │ │ │
│  │    → PDF Report      │  │  │ (Yahoo Fin)│ │ (News APIs) │ │ │
│  │                      │  │  └─────┬──────┘ └──────┬──────┘ │ │
│  │  Job 2: 8:30 AM IST  │  │        │               │        │ │
│  │    → Dashboard       │  │  ┌─────▼───────────────▼──────┐ │ │
│  │    (Mon-Fri only)    │  │  │   Technical Analysis       │ │ │
│  │                      │  │  │   Engine (Python)          │ │ │
│  └──────────────────────┘  │  └─────┬──────────────────────┘ │ │
│                            │        │                         │ │
│  ┌──────────────────────┐  │  ┌─────▼──────────────────────┐ │ │
│  │  PDF GENERATOR       │  │  │   Report / Dashboard       │ │ │
│  │  (ReportLab +        │  │  │   Builder                  │ │ │
│  │   Matplotlib)        │  │  └────────────────────────────┘ │ │
│  └──────────────────────┘  └──────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                        DATA LAYER                               │
│  ┌──────────────────┐  ┌───────────────┐  ┌──────────────────┐ │
│  │  PostgreSQL       │  │  Redis         │  │  File Storage    │ │
│  │  - stocks         │  │  - job state   │  │  (S3 / local)    │ │
│  │  - ohlcv_daily    │  │  - cache       │  │  - PDF reports   │ │
│  │  - ta_results     │  │  - rate limits │  │  - dashboard HTML│ │
│  │  - reports_meta   │  │               │  │  - chart images  │ │
│  │  - news_cache     │  │               │  │                  │ │
│  └──────────────────┘  └───────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack Recommendation

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Language** | Python 3.11+ | TA libraries (pandas, numpy), PDF generation (reportlab), data science ecosystem |
| **Web Framework** | FastAPI | Async support, auto-generated OpenAPI docs, type validation via Pydantic |
| **Task Scheduler** | Celery + Celery Beat (Redis broker) | Reliable cron-like scheduling, retry logic, distributed execution |
| **Database** | PostgreSQL 15+ | Time-series queries, JSONB for flexible TA results, mature ecosystem |
| **Cache** | Redis 7+ | Job state, API response caching, rate limit tracking |
| **File Storage** | S3-compatible (MinIO for self-hosted, AWS S3 for cloud) | PDF and HTML artifact storage with versioning |
| **Frontend** | Next.js 14 (React) | SSR for SEO, API routes, static export option |
| **Charting** | Lightweight Charts v4 (TradingView) | Open-source, fast candlestick rendering, small bundle |
| **PDF Engine** | ReportLab + Matplotlib | Programmatic PDF with embedded charts |
| **Market Data** | Yahoo Finance API (v8 chart endpoint) | Free, reliable for Indian stocks (NSE/BSE) |
| **News/Sentiment** | Google News RSS + NewsAPI + web scraping | Multi-source for sentiment coverage |
| **Deployment** | Docker Compose (dev), Kubernetes (prod) | Container orchestration, easy scaling |
| **CI/CD** | GitHub Actions | Automated testing, Docker builds, deployment |

---

## 4. Watchlist — Stock Universe

These 9 stocks are the current watchlist. The system should support adding/removing stocks via an admin API.

| # | Company | Ticker (Yahoo) | Exchange | ISIN | Sector |
|---|---------|----------------|----------|------|--------|
| 1 | Vodafone Idea | IDEA.NS | NSE | INE669E01016 | Telecom |
| 2 | Aurobindo Pharma | AUROPHARMA.NS | NSE | INE406A01037 | Pharma |
| 3 | NCC Limited | NCC.NS | NSE | INE868B01028 | Infrastructure |
| 4 | HCC | HCC.NS | NSE | INE549A01026 | Infrastructure |
| 5 | Adani Green Energy | ADANIGREEN.NS | NSE | INE364U01010 | Renewable Energy |
| 6 | Adani Power | ADANIPOWER.NS | NSE | INE814H01029 | Power |
| 7 | Waaree Energies | WAAREEENER.NS | NSE | INE377N01017 | Solar/Energy |
| 8 | Groww (Billionbrains) | GROWW.NS | NSE | INE0HOQ01053 | Fintech |
| 9 | Digilogic Systems | DIGILOGIC.BO | BSE | INE1OOT01028 | IT/Micro-cap |

**Note:** DIGILOGIC trades on BSE only; use `.BO` suffix for Yahoo Finance.

---

## 5. Data Models

### 5.1 Database Schema (PostgreSQL)

```sql
-- Core stock registry
CREATE TABLE stocks (
    id            SERIAL PRIMARY KEY,
    ticker        VARCHAR(20) UNIQUE NOT NULL,    -- e.g. 'IDEA.NS'
    display_key   VARCHAR(20) NOT NULL,            -- e.g. 'IDEA'
    company_name  VARCHAR(100) NOT NULL,
    isin          VARCHAR(12),
    exchange      VARCHAR(5) NOT NULL,             -- 'NSE' or 'BSE'
    sector        VARCHAR(50),
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Daily OHLCV price data
CREATE TABLE ohlcv_daily (
    id         BIGSERIAL PRIMARY KEY,
    stock_id   INT NOT NULL REFERENCES stocks(id),
    date       DATE NOT NULL,
    open       DECIMAL(12,2) NOT NULL,
    high       DECIMAL(12,2) NOT NULL,
    low        DECIMAL(12,2) NOT NULL,
    close      DECIMAL(12,2) NOT NULL,
    volume     BIGINT NOT NULL DEFAULT 0,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (stock_id, date)
);

CREATE INDEX idx_ohlcv_stock_date ON ohlcv_daily(stock_id, date DESC);

-- Technical analysis results (computed daily)
CREATE TABLE ta_results (
    id              BIGSERIAL PRIMARY KEY,
    stock_id        INT NOT NULL REFERENCES stocks(id),
    computed_date   DATE NOT NULL,
    timeframe       VARCHAR(10) NOT NULL,   -- 'daily' or 'weekly'
    ema20           JSONB,                  -- [{time, value}, ...]
    ema50           JSONB,
    support_levels  JSONB,                  -- [{price, strength}, ...]
    resistance_levels JSONB,
    stop_loss       JSONB,                  -- {stop_loss, atr, method}
    bull_bear_runs  JSONB,                  -- [{type, start, end}, ...]
    week52_high     DECIMAL(12,2),
    week52_low      DECIMAL(12,2),
    current_price   DECIMAL(12,2),
    day_change      DECIMAL(12,2),
    day_change_pct  DECIMAL(6,2),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (stock_id, computed_date, timeframe)
);

-- Fundamental research cache
CREATE TABLE fundamental_research (
    id              BIGSERIAL PRIMARY KEY,
    stock_id        INT NOT NULL REFERENCES stocks(id),
    report_date     DATE NOT NULL,
    financials      JSONB,     -- revenue growth, ROE, D/E, P/E, P/B
    sentiment       JSONB,     -- media sentiment, tailwinds, headwinds
    governance      JSONB,     -- management changes, regulatory news
    analyst_consensus JSONB,   -- buy/hold/sell %, target prices
    risk_factors    JSONB,     -- volatility, annual report risks
    verdict         VARCHAR(10),  -- 'Positive' / 'Neutral' / 'Negative'
    verdict_reason  TEXT,
    plain_english   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (stock_id, report_date)
);

-- Government investment tracker
CREATE TABLE govt_investments (
    id              BIGSERIAL PRIMARY KEY,
    report_date     DATE NOT NULL,
    company_name    VARCHAR(100),
    ticker          VARCHAR(20),
    announcement    TEXT NOT NULL,
    announcement_date DATE,
    plain_english   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Generated reports metadata
CREATE TABLE reports (
    id              BIGSERIAL PRIMARY KEY,
    report_type     VARCHAR(20) NOT NULL,   -- 'pdf_watchlist' or 'html_dashboard'
    report_date     DATE NOT NULL,
    file_path       TEXT NOT NULL,           -- S3 key or local path
    file_size_kb    INT,
    stocks_covered  JSONB,                   -- ['IDEA', 'AUROPHARMA', ...]
    generation_time_seconds DECIMAL(6,1),
    status          VARCHAR(20) DEFAULT 'completed',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### 5.2 Pydantic Models (API Layer)

```python
from pydantic import BaseModel
from datetime import date
from typing import Optional

class Stock(BaseModel):
    id: int
    ticker: str
    display_key: str
    company_name: str
    isin: Optional[str]
    exchange: str
    sector: Optional[str]
    is_active: bool

class OHLCVCandle(BaseModel):
    time: str          # 'YYYY-MM-DD'
    open: float
    high: float
    low: float
    close: float
    volume: int

class SupportResistanceLevel(BaseModel):
    price: float
    strength: int      # number of touches

class StopLossResult(BaseModel):
    stop_loss: float
    atr: float
    method: str

class BullBearRun(BaseModel):
    type: str          # 'bull' or 'bear'
    start: str         # 'YYYY-MM-DD'
    end: str

class TimeframeAnalysis(BaseModel):
    candles: list[OHLCVCandle]
    ema20: list[dict]  # [{time, value}]
    ema50: list[dict]
    support: list[SupportResistanceLevel]
    resistance: list[SupportResistanceLevel]
    stop_loss: StopLossResult
    bull_bear_runs: list[BullBearRun]

class StockDashboardData(BaseModel):
    name: str
    ticker: str
    current_price: float
    day_change: float
    day_change_pct: float
    week52_high: float
    week52_low: float
    daily: TimeframeAnalysis
    weekly: TimeframeAnalysis

class FundamentalVerdict(BaseModel):
    verdict: str       # 'Positive' / 'Neutral' / 'Negative'
    reason: str
    plain_english: str

class ReportMetadata(BaseModel):
    report_type: str
    report_date: date
    file_url: str
    stocks_covered: list[str]
```

---

## 6. Scheduled Jobs

### 6.1 Job 1: Daily PDF Watchlist Report

| Property | Value |
|----------|-------|
| **Job ID** | `daily-stock-watchlist-pdf-report` |
| **Schedule** | `0 8 * * *` (8:00 AM IST, every day) |
| **Timeout** | 15 minutes |
| **Retry** | 2 retries with 60s backoff |

**Pipeline:**

```
[1] Fetch market data (Yahoo Finance API)
         │
[2] Scrape news & sentiment (Google News, financial sites)
         │
[3] Aggregate analyst consensus (brokerage reports, screeners)
         │
[4] Compile fundamental research per stock (A–D framework)
         │
[5] Search government investment news (last 1–2 weeks)
         │
[6] Generate PDF (ReportLab + Matplotlib)
         │
[7] Store PDF → S3/filesystem
         │
[8] Update reports table
         │
[9] Deliver (email / API / notification)
```

**PDF Report Structure:**

```
Page 1: Cover
  ├── Title: "Daily Stock Watchlist Report — {date}"
  ├── Quick-scan summary table (9 rows)
  │     Columns: Stock | Ticker | Verdict (color-coded) | 1Y Change %
  ├── Sentiment Overview Bar Chart (horizontal, color-coded)
  ├── 1-Year Price Performance Bar Chart
  └── P/E Valuation Snapshot Bar Chart

Pages 2–10: Per-Stock Sections (1–2 pages each)
  ├── Header bar (navy): Company Name | Ticker | ISIN | Verdict badge
  ├── Section A — Financial Performance
  │     Revenue/profit growth (3–5 year), ROE vs peers, D/E ratio,
  │     P/E and P/B vs historical average
  ├── Section B — Market Sentiment & Narrative
  │     Media sentiment, tailwinds, headwinds, governance news
  ├── Section C — Professional Consensus
  │     Analyst Buy/Hold/Sell %, target price ranges
  ├── Section D — Risk & Context
  │     Risk factors from annual report, volatility vs Nifty 50
  ├── Quick Verdict: one-line synthesis
  ├── Pre-market signals (global cues, SGX Nifty, US overnight)
  └── IN PLAIN ENGLISH: 2–3 sentence jargon-free summary

Pages 11–12: Government Investment Tracker
  └── Table: Company | Ticker | Announcement | Date | Plain English
```

**Research Framework (per stock):**

| Section | Data Points | Sources |
|---------|------------|---------|
| A. Financials | Revenue/profit growth (3–5Y), ROE, D/E, P/E, P/B | Screener.in, Moneycontrol, annual reports |
| B. Sentiment | Media mood, sector tailwinds/headwinds, governance | Google News, Economic Times, Mint |
| C. Consensus | Buy/Hold/Sell %, target prices | Trendlyne, TipRanks, broker reports |
| D. Risk | Annual report risks, beta vs Nifty 50 | BSE/NSE filings, Yahoo Finance |
| E. Output | Verdict (Pos/Neut/Neg), plain English summary | Synthesized from A–D |

**Rules:**
- Descriptive analysis only — never say "buy" or "sell"
- Every data point must be sourced; no skipping
- Plain English sections must avoid unexplained jargon
- Pre-market signals include global cues (US markets overnight, SGX Nifty)

### 6.2 Job 2: Daily Technical Dashboard

| Property | Value |
|----------|-------|
| **Job ID** | `daily-stock-technical-dashboard` |
| **Schedule** | `30 8 * * 1-5` (8:30 AM IST, weekdays only) |
| **Timeout** | 10 minutes |
| **Retry** | 2 retries with 30s backoff |

**Pipeline:**

```
[1] Fetch 6-month OHLCV data (Yahoo Finance v8 Chart API)
         │
[2] Fetch 1-year data for 52-week high/low
         │
[3] Run Technical Analysis Engine
    ├── EMA(20), EMA(50) — daily
    ├── EMA(10), EMA(20) — weekly
    ├── ATR(14)
    ├── Fractal pivot detection → Support/Resistance clustering
    ├── ATR-based stop loss with fallback
    ├── EMA crossover bull/bear zone detection
    └── Weekly resampling
         │
[4] Build self-contained HTML dashboard
         │
[5] Store HTML → S3/filesystem
         │
[6] Update reports table
         │
[7] Deliver (serve via API / notification)
```

---

## 7. Technical Analysis Algorithms — Full Specification

### 7.1 Exponential Moving Average (EMA)

**Purpose:** Trend-following indicator. EMA(20)/EMA(50) crossovers identify bull/bear transitions.

**Parameters:**
- Daily chart: span = 20 and span = 50
- Weekly chart: span = 10 and span = 20

**Algorithm:**
```
k = 2 / (span + 1)
EMA[0] = close[0]
EMA[i] = close[i] * k + EMA[i-1] * (1 - k)    for i >= 1
```

**Output:** Array of `{time: "YYYY-MM-DD", value: float}` for overlay on candlestick chart.

---

### 7.2 Average True Range (ATR)

**Purpose:** Measures volatility. Used as input for stop loss calculation.

**Parameters:** period = 14

**Algorithm:**
```
TR[0] = high[0] - low[0]
TR[i] = max(
    high[i] - low[i],
    |high[i] - close[i-1]|,
    |low[i] - close[i-1]|
)    for i >= 1

ATR[13] = mean(TR[0..13])                        // first ATR: simple average
ATR[i]  = (ATR[i-1] * 13 + TR[i]) / 14           for i >= 14   // Wilder smoothing
```

**Output:** Single float value (latest ATR) used by stop loss calculator.

---

### 7.3 Fractal Pivot Detection

**Purpose:** Identify swing highs and swing lows — the raw material for support/resistance levels.

**Parameters:** window = 3 and window = 5 (run both, merge results)

**Algorithm:**
```
For each candle i in range [window, N-window]:
    If high[i] == max(high[i-window .. i+window]):
        → swing_high at (index=i, price=high[i])
    If low[i] == min(low[i-window .. i+window]):
        → swing_low at (index=i, price=low[i])
```

**Output:** Two lists — `swing_highs[(index, price)]` and `swing_lows[(index, price)]`.

---

### 7.4 Price Level Clustering (Support/Resistance)

**Purpose:** Group nearby swing points into meaningful price levels with a "strength" score.

**Parameters:** tolerance = 1.5% of price, minimum_touches = 2

**Algorithm:**
```
Sort all swing prices ascending.
Initialize cluster = [prices[0]]

For each price p in prices[1..]:
    If |p - mean(cluster)| / mean(cluster) < 0.015:
        cluster.append(p)
    Else:
        Emit {price: mean(cluster), strength: len(cluster)}
        cluster = [p]
Emit final cluster.

Filter: keep only clusters with strength >= 2.
```

**Post-processing:**
- Resistance levels: clustered swing highs where `price > current_price * 0.98`. Sort by strength descending, take top 4.
- Support levels: clustered swing lows where `price < current_price * 1.02`. Sort by strength descending, take top 4.

**Output:**
```json
{
  "support": [{"price": 130.39, "strength": 3}, ...],
  "resistance": [{"price": 161.53, "strength": 4}, ...]
}
```

---

### 7.5 Stop Loss (ATR-Based with Fallback)

**Purpose:** Compute a defensive exit level below current price.

**Algorithm:**
```
1. Find recent swing low (last 25 candles, fractal window=3):
   swing_low = min(price) among recent swing lows
   Fallback: min(low[last 20 candles])

2. ATR stop:
   atr_stop = swing_low - (ATR_14 * 0.5)

3. Chandelier stop:
   highest_high = max(high[last 22 candles])
   chandelier_stop = highest_high - (ATR_14 * 2.0)

4. Primary stop loss:
   stop_loss = max(atr_stop, chandelier_stop)

5. FALLBACK (critical for downtrending stocks):
   If stop_loss >= current_price:
       stop_loss = max(
           current_price - 1.5 * ATR_14,
           min(low[last 30 candles])
       )
```

**Output:**
```json
{
  "stop_loss": 135.83,
  "atr": 3.42,
  "method": "ATR-based"
}
```

---

### 7.6 Bull/Bear Zone Detection (EMA Crossover)

**Purpose:** Classify market regime as bullish or bearish based on EMA relationship.

**Algorithm:**
```
Compute EMA(20) and EMA(50) for each candle.

current_zone = null
zones = []

For each candle i:
    zone_type = "bull" if EMA20[i] > EMA50[i] else "bear"
    
    If current_zone is null:
        current_zone = {type: zone_type, start: date[i]}
    Elif zone_type != current_zone.type:
        current_zone.end = date[i-1]
        zones.append(current_zone)
        current_zone = {type: zone_type, start: date[i]}

current_zone.end = date[last]
zones.append(current_zone)
```

**Output:**
```json
[
  {"type": "bear", "start": "2026-01-30", "end": "2026-04-06"},
  {"type": "bull", "start": "2026-04-07", "end": "2026-06-15"},
  {"type": "bear", "start": "2026-06-16", "end": "2026-07-30"}
]
```

---

### 7.7 Weekly Resampling

**Purpose:** Convert daily OHLCV into weekly candles for the weekly chart view.

**Algorithm:**
```
Group daily candles by ISO week (Monday = week start).

For each week:
    open   = first candle's open
    high   = max(all highs in week)
    low    = min(all lows in week)
    close  = last candle's close
    volume = sum(all volumes in week)
```

Weekly TA uses EMA(10)/EMA(20) instead of EMA(20)/EMA(50).

---

### 7.8 52-Week High/Low

**Purpose:** Show the stock's price position within its 1-year trading range.

**Algorithm:**
```
Fetch 1-year OHLCV data (range=1y).
week52_high = max(all daily highs)
week52_low  = min(all daily lows)
position_pct = (current_price - week52_low) / (week52_high - week52_low) * 100
```

**Output:** `{week52_high: 225.95, week52_low: 130.00}`

---

## 8. External APIs

### 8.1 Yahoo Finance v8 Chart API

**Base URL:** `https://query1.finance.yahoo.com/v8/finance/chart/`

**6-Month Daily OHLCV:**
```
GET /v8/finance/chart/{SYMBOL}?range=6mo&interval=1d&includePrePost=false

Response shape:
{
  "chart": {
    "result": [{
      "timestamp": [1706572200, ...],          // Unix timestamps
      "indicators": {
        "quote": [{
          "open": [143.92, ...],
          "high": [147.49, ...],
          "low": [141.9, ...],
          "close": [146.43, ...],
          "volume": [2599299, ...]
        }]
      }
    }]
  }
}
```

**1-Year Daily (for 52-week range):**
```
GET /v8/finance/chart/{SYMBOL}?range=1y&interval=1d&includePrePost=false
```

**Rate Limits:** No official docs, but ~2000 requests/hour appears safe. Implement 200ms delay between requests.

**CORS Note:** This API blocks cross-origin requests from `file://` origins. When fetching from a browser, navigate to `finance.yahoo.com` first (same-origin). For server-side, no CORS issue.

**Ticker Format:**
- NSE stocks: `{SYMBOL}.NS` (e.g., `IDEA.NS`)
- BSE stocks: `{SYMBOL}.BO` (e.g., `DIGILOGIC.BO`)

### 8.2 News & Sentiment Sources

| Source | Method | Data |
|--------|--------|------|
| Google News RSS | `GET https://news.google.com/rss/search?q={company}+stock` | Headlines, links |
| NewsAPI.org | REST API with API key | Full articles, sentiment |
| Moneycontrol | Web scrape | Analyst ratings, financials |
| Screener.in | Web scrape | Financial ratios, peer comparison |
| Trendlyne | Web scrape | Analyst consensus, target prices |
| NSE/BSE filings | Web scrape | Annual reports, corporate actions |

---

## 9. API Specification

### 9.1 Endpoints

#### Stocks

```
GET    /api/stocks                    → List all active stocks
GET    /api/stocks/{ticker}           → Get stock details + latest TA
POST   /api/stocks                    → Add stock to watchlist (admin)
DELETE /api/stocks/{ticker}           → Remove stock (admin)
```

#### Dashboard Data

```
GET /api/dashboard/latest            → Latest dashboard data for all stocks
GET /api/dashboard/{ticker}          → Single stock dashboard data
GET /api/dashboard/{ticker}/candles  → OHLCV candles (query: timeframe=daily|weekly, range=6mo|1y)
```

#### Reports

```
GET /api/reports/latest              → Latest PDF report metadata + download URL
GET /api/reports/history             → List of past reports (paginated)
GET /api/reports/{id}/download       → Download PDF file
```

#### Scheduler

```
GET    /api/scheduler/jobs           → List all scheduled jobs with status
POST   /api/scheduler/jobs/{id}/run  → Trigger immediate run (admin)
PATCH  /api/scheduler/jobs/{id}      → Enable/disable a job (admin)
```

#### Health

```
GET /api/health                      → Service health + last job run times
```

### 9.2 Example Response: `GET /api/dashboard/latest`

```json
{
  "generated_at": "2026-07-30T08:30:00+05:30",
  "stocks": {
    "IDEA": {
      "name": "Vodafone Idea",
      "ticker": "IDEA",
      "current_price": 13.00,
      "day_change": -0.05,
      "day_change_pct": -0.38,
      "week52_high": 15.34,
      "week52_low": 6.12,
      "daily": {
        "candles": [{"time":"2026-01-30","open":9.96,"high":11.38,"low":9.86,"close":11.17,"volume":656772821}, ...],
        "ema20": [{"time":"2026-01-30","value":11.17}, ...],
        "ema50": [{"time":"2026-01-30","value":11.17}, ...],
        "support": [{"price":8.13,"strength":2}, {"price":9.37,"strength":3}],
        "resistance": [{"price":15.27,"strength":2}, {"price":14.85,"strength":3}],
        "stop_loss": {"stop_loss":12.76,"atr":0.32,"method":"ATR-based"},
        "bull_bear_runs": [{"type":"bear","start":"2026-01-30","end":"2026-04-06"}, ...]
      },
      "weekly": { ... }
    },
    "AUROPHARMA": { ... },
    ...
  }
}
```

### 9.3 Example Response: `GET /api/reports/latest`

```json
{
  "id": 42,
  "report_type": "pdf_watchlist",
  "report_date": "2026-07-30",
  "download_url": "/api/reports/42/download",
  "file_size_kb": 1250,
  "stocks_covered": ["IDEA","AUROPHARMA","NCC","HCC","ADANIGREEN","ADANIPOWER","WAAREEENER","GROWW","DIGILOGIC"],
  "generation_time_seconds": 45.2,
  "created_at": "2026-07-30T08:05:12+05:30"
}
```

---

## 10. Frontend Specification

### 10.1 Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Home / Dashboard | Interactive technical chart + info panel |
| `/reports` | Report Archive | List of past PDF reports with download links |
| `/settings` | Settings (admin) | Manage watchlist, scheduler controls |

### 10.2 Dashboard Page — Component Tree

```
<DashboardPage>
  ├── <Header>                    Title, date, refresh button
  ├── <StockTabs>                 9 tabs: ticker + daily change %
  │     └── <Tab key="IDEA">     Active state: blue highlight
  ├── <ControlBar>
  │     ├── <TimeframeToggle>    [Daily] [Weekly]
  │     └── <Legend>              Color swatches for all indicators
  ├── <MainContent>
  │     ├── <ChartArea>           Lightweight Charts container
  │     │     ├── CandlestickSeries (green up / red down)
  │     │     ├── VolumeSeries     (bottom 15%, colored by direction)
  │     │     ├── LineSeries       EMA20 (#58a6ff, 1px solid)
  │     │     ├── LineSeries       EMA50 (#d2a8ff, 1px solid)
  │     │     ├── PriceLine        Stop Loss (#f0883e, 2px dashed)
  │     │     ├── PriceLine[]      Support (#3fb950, 1px dashed)
  │     │     ├── PriceLine[]      Resistance (#f85149, 1px dashed)
  │     │     ├── PriceLine        52W High (#e3b341, 1px dotted)
  │     │     ├── PriceLine        52W Low (#a371f7, 1px dotted)
  │     │     └── Markers[]        Bull/Bear zone transitions
  │     └── <InfoPanel>            280px right sidebar
  │           ├── <StockInfo>      Name, price, change, trend badge
  │           ├── <Week52Range>    High, low, visual position bar
  │           ├── <StopLoss>       Level, ATR, risk %
  │           ├── <SupportLevels>  Price, touch count, distance %
  │           ├── <ResistanceLevels>
  │           └── <TrendZones>     Last 4 bull/bear zones
  └── <Footer>                    Last updated timestamp
```

### 10.3 Design Tokens

```css
/* Colors */
--bg-primary:      #0a0e17;
--bg-secondary:    #0d1117;
--bg-card:         #161b22;
--border:          #21262d;
--border-active:   #30363d;
--text-primary:    #e1e4e8;
--text-secondary:  #8b949e;
--text-muted:      #6e7681;

/* Indicator Colors */
--color-bullish:   #3fb950;
--color-bearish:   #f85149;
--color-stop-loss: #f0883e;
--color-ema20:     #58a6ff;
--color-ema50:     #d2a8ff;
--color-52w-high:  #e3b341;
--color-52w-low:   #a371f7;
--color-tab-active:#1f6feb;
--color-toggle-on: #238636;

/* Spacing */
--gap-sm: 4px;
--gap-md: 8px;
--gap-lg: 16px;

/* Typography */
--font-family: 'Segoe UI', system-ui, sans-serif;
--font-size-sm: 11px;
--font-size-base: 13px;
--font-size-lg: 18px;
```

### 10.4 Responsive Behavior

| Breakpoint | Layout |
|-----------|--------|
| > 900px | Side-by-side: chart area (flex:1) + info panel (280px) |
| ≤ 900px | Stacked: chart on top, info panel below (200px height, scrollable) |

---

## 11. PDF Report Generation

### 11.1 Library: ReportLab + Matplotlib

**Chart Generation (Matplotlib → PNG → embed in PDF):**

```python
# 1. Sentiment Overview (horizontal bar chart)
#    Color: green (#3fb950) for Positive, amber (#f0883e) for Neutral, red (#f85149) for Negative
#    One bar per stock, labeled with verdict text

# 2. 1-Year Price Performance (bar chart)
#    Shows % change over trailing 1 year for each stock

# 3. P/E Valuation Snapshot (grouped bar chart)
#    Current P/E vs sector average for each stock
```

**PDF Layout (ReportLab Platypus):**

```python
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer, KeepTogether, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# Per-stock section wrapped in KeepTogether to prevent awkward page breaks
# Navy header bar: 100% width, white text, company name + ticker + ISIN
# Verdict badge: colored rectangle inline with header
# Data table: alternating row colors, 6 rows (Sections A–D + Verdict + Plain English)
# PageBreak only before Part 1 start and Part 2 start
```

---

## 12. Deployment Architecture

### 12.1 Docker Compose (Development / Single-Server)

```yaml
version: '3.8'
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://user:pass@db:5432/stockwatch
      REDIS_URL: redis://redis:6379/0
      S3_BUCKET: stock-reports
    depends_on: [db, redis]

  scheduler:
    build: ./backend
    command: celery -A app.celery beat --loglevel=info
    environment:
      DATABASE_URL: postgresql://user:pass@db:5432/stockwatch
      REDIS_URL: redis://redis:6379/0
    depends_on: [db, redis]

  worker:
    build: ./backend
    command: celery -A app.celery worker --loglevel=info --concurrency=2
    environment:
      DATABASE_URL: postgresql://user:pass@db:5432/stockwatch
      REDIS_URL: redis://redis:6379/0
    depends_on: [db, redis]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [api]

  db:
    image: postgres:15
    volumes: ["pgdata:/var/lib/postgresql/data"]
    environment:
      POSTGRES_DB: stockwatch
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass

  redis:
    image: redis:7-alpine

volumes:
  pgdata:
```

### 12.2 Production Considerations

- **HTTPS:** Nginx reverse proxy with Let's Encrypt SSL
- **Authentication:** JWT-based auth for admin endpoints; dashboard can be public or behind login
- **Monitoring:** Prometheus metrics + Grafana dashboard for job success rates, API latency
- **Alerting:** PagerDuty/Slack webhook if a scheduled job fails
- **Backup:** Daily PostgreSQL pg_dump to S3
- **Scaling:** Worker pods can scale horizontally; scheduler must be singleton

---

## 13. Error Handling & Edge Cases

| Scenario | Handling |
|----------|----------|
| Yahoo Finance API down | Retry 3x with exponential backoff (2s, 4s, 8s). If all fail, use previous day's cached data and flag report as "stale." |
| Stock delisted / ticker change | `ohlcv_daily` fetch returns empty. Log warning, skip stock, include "Data unavailable" note in report. |
| Market holiday (volume=0 candles) | Keep in dataset. TA algorithms handle gracefully (no division by zero). |
| Stop loss computed above current price | Fallback: `max(price - 1.5*ATR, min(low[30]))`. This handles strongly downtrending stocks. |
| Fewer than 30 data points for a stock | Skip TA for that stock. Show "Insufficient data" in dashboard. |
| PDF generation fails | Retry once. If still fails, send alert and serve previous day's PDF. |
| Concurrent job execution | Celery's `solo` pool or Redis lock ensures at most one instance of each job. |

---

## 14. Project Structure

```
stock-watchlist-platform/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app
│   │   ├── config.py                # Settings (env vars)
│   │   ├── celery.py                # Celery app + beat schedule
│   │   ├── models/
│   │   │   ├── database.py          # SQLAlchemy models
│   │   │   └── schemas.py           # Pydantic schemas
│   │   ├── api/
│   │   │   ├── stocks.py            # /api/stocks endpoints
│   │   │   ├── dashboard.py         # /api/dashboard endpoints
│   │   │   ├── reports.py           # /api/reports endpoints
│   │   │   └── scheduler.py         # /api/scheduler endpoints
│   │   ├── services/
│   │   │   ├── market_data.py       # Yahoo Finance fetcher
│   │   │   ├── news_fetcher.py      # News & sentiment scraper
│   │   │   ├── ta_engine.py         # All TA algorithms (§7)
│   │   │   ├── pdf_generator.py     # ReportLab PDF builder
│   │   │   └── dashboard_builder.py # HTML dashboard generator
│   │   └── tasks/
│   │       ├── pdf_report.py        # Celery task: daily PDF
│   │       └── dashboard.py         # Celery task: daily dashboard
│   ├── tests/
│   │   ├── test_ta_engine.py
│   │   ├── test_market_data.py
│   │   └── test_api.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx             # Dashboard page
│   │   │   ├── reports/page.tsx     # Reports archive
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── StockTabs.tsx
│   │   │   ├── ChartArea.tsx        # Lightweight Charts wrapper
│   │   │   ├── InfoPanel.tsx
│   │   │   ├── Week52Range.tsx
│   │   │   └── TimeframeToggle.tsx
│   │   ├── lib/
│   │   │   └── api.ts               # API client
│   │   └── styles/
│   │       └── tokens.css           # Design tokens (§10.3)
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 15. Testing Strategy

| Type | Scope | Tool |
|------|-------|------|
| **Unit** | TA algorithms (EMA, ATR, fractals, clustering, stop loss) | pytest |
| **Unit** | API endpoint logic | pytest + httpx |
| **Integration** | Data pipeline: fetch → analyze → store → generate | pytest + test DB |
| **E2E** | Full scheduled job execution with mock data | pytest + Celery test worker |
| **Frontend** | Component rendering, chart initialization | Jest + React Testing Library |
| **Visual** | Dashboard renders correctly across browsers | Playwright screenshots |

**Critical test cases for TA engine:**
- EMA convergence on constant series → EMA equals constant
- ATR on single candle → returns high-low
- Fractal detection on known pattern (V-shape) → finds exact bottom
- Stop loss fallback triggers when chandelier > current price
- Clustering merges levels within 1.5% but separates beyond
- Weekly resampling with partial week at boundaries

---

## 16. Future Enhancements

- **Real-time mode:** WebSocket feed from NSE/BSE for live price updates during market hours
- **Alerts:** Push notifications when price crosses support/resistance or stop loss
- **Backtesting:** Historical accuracy of computed stop loss and S/R levels
- **Portfolio tracking:** Track buy price, P&L, allocation
- **Additional indicators:** RSI, MACD, Bollinger Bands (toggleable overlays)
- **Multi-user:** User accounts with personalized watchlists
- **Mobile app:** React Native wrapper around the dashboard
- **AI sentiment scoring:** LLM-based sentiment classification on news articles with confidence scores
