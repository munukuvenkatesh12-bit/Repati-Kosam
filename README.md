# Stock Watchlist Platform

Automated daily pre-market analysis for 9 Indian stocks. Zero-cost infrastructure using GitHub Actions + GitHub Pages + SendGrid email.

## Folder Structure

```
stock-watchlist/
├── docs/                              ← Design documents
│   ├── Technical_Design_Document_v1.md    Full-stack TDD (server-based architecture)
│   └── Technical_Design_Document_v2.md    GitHub Pages TDD (zero-cost, current)
│
├── scripts/                           ← Production codebase (deploy this)
│   ├── config.py                          Stock list, TA parameters, settings
│   ├── fetch_data.py                      Yahoo Finance OHLCV fetcher
│   ├── ta_engine.py                       All TA algorithms (EMA, ATR, S/R, stop loss, etc.)
│   ├── generate_dashboard.py              Interactive HTML dashboard builder
│   ├── generate_email.py                  Email HTML + chart image generator
│   ├── generate_archive_index.py          Archive page auto-generator
│   └── send_email.py                      SendGrid / Gmail email sender
│
├── site/                              ← Static website (deployed to GitHub Pages)
│   └── index.html                         Landing page
│
├── tests/                             ← Unit tests
│   └── test_ta_engine.py                  18 tests for all TA algorithms
│
├── samples/                           ← Sample outputs (reference/demo)
│   ├── Stock_Technical_Dashboard.html     Working dashboard with real data (open in browser)
│   ├── Daily_Stock_Watchlist_Report_2026-07-30.pdf   Sample PDF report
│   ├── fetch_and_analyze.py               Standalone TA script (all-in-one version)
│   ├── generate_report.py                 PDF report generator (ReportLab)
│   ├── charts/                            Sample chart images used in PDF
│   └── data/                              Sample JSON data from analysis runs
│
├── .github/workflows/
│   └── daily-update.yml               ← GitHub Actions cron workflow
│
├── requirements.txt                   ← Python dependencies
├── .gitignore
└── README.md                          ← This file
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/{you}/stock-watchlist.git && cd stock-watchlist

# 2. Install
pip install -r requirements.txt

# 3. Run locally
cd scripts
python fetch_data.py           # Fetch market data
python ta_engine.py            # Run technical analysis
python generate_dashboard.py   # Build interactive dashboard
python generate_email.py       # Build email + chart images

# 4. Open results
open ../site/dashboard/index.html
```

## Deploy (GitHub Pages + daily email)

1. Push this repo to GitHub
2. Add secrets: `SENDGRID_API_KEY`, `EMAIL_TO`
3. Add variable: `SITE_URL` = `https://{you}.github.io/stock-watchlist`
4. Enable GitHub Pages (Settings → Pages → Branch: `gh-pages`)
5. Done — runs automatically at 8:00 AM and 8:25 AM IST

## Stocks Covered

IDEA · AUROPHARMA · NCC · HCC · ADANIGREEN · ADANIPOWER · WAAREEENER · GROWW · DIGILOGIC

Edit `scripts/config.py` to add or remove stocks.
