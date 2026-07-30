"""
Stock Watchlist Platform — Configuration
All tuneable parameters in one place.
"""
import os
from pathlib import Path

# ─── Repository root (works both locally and in GitHub Actions) ───
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"
CHART_DIR = SITE_DIR / "assets" / "charts"

# Ensure dirs exist
DATA_DIR.mkdir(exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)

# ─── Stock Universe ───
STOCKS = [
    {"ticker": "IDEA.NS",       "key": "IDEA",       "name": "Vodafone Idea",     "sector": "Telecom"},
    {"ticker": "AUROPHARMA.NS", "key": "AUROPHARMA", "name": "Aurobindo Pharma",  "sector": "Pharma"},
    {"ticker": "NCC.NS",        "key": "NCC",        "name": "NCC Limited",        "sector": "Infrastructure"},
    {"ticker": "HCC.NS",        "key": "HCC",        "name": "HCC",                "sector": "Infrastructure"},
    {"ticker": "ADANIGREEN.NS", "key": "ADANIGREEN", "name": "Adani Green Energy", "sector": "Renewable Energy"},
    {"ticker": "ADANIPOWER.NS", "key": "ADANIPOWER", "name": "Adani Power",        "sector": "Power"},
    {"ticker": "WAAREEENER.NS", "key": "WAAREEENER", "name": "Waaree Energies",   "sector": "Solar/Energy"},
    {"ticker": "GROWW.NS",      "key": "GROWW",      "name": "Groww",              "sector": "Fintech"},
    {"ticker": "DIGILOGIC.BO",  "key": "DIGILOGIC",  "name": "Digilogic Systems", "sector": "IT/Micro-cap"},
]

# ─── Yahoo Finance API ───
YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
FETCH_DELAY = 0.2          # seconds between requests
FETCH_RETRIES = 3
FETCH_BACKOFF = [1, 2, 4]  # seconds per retry

# ─── TA Parameters ───
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

# ─── Email ───
EMAIL_FROM = os.getenv("EMAIL_FROM", "Stock Watchlist <noreply@stockwatch.dev>")
MAIL_TO = os.getenv("MAIL_TO", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SITE_URL = os.getenv("SITE_URL", "https://yourusername.github.io/stock-watchlist")

# ─── Archive ───
ARCHIVE_KEEP_DAYS = 90
