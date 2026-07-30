"""
Generate email-safe HTML body + static chart images for email embedding.
Input:  data/ta_results.json
Output: data/email_body.html, site/assets/charts/*.png

Email HTML uses:
- Table-based layout (no flexbox/grid)
- Inline CSS only (Gmail strips <style> blocks)
- Chart images hosted on GitHub Pages (referenced by absolute URL)
- Max width 600px
"""
import json
import sys
import os
from datetime import datetime, timezone, timedelta

from config import DATA_DIR, CHART_DIR, SITE_URL

IST = timezone(timedelta(hours=5, minutes=30))

# Try to import matplotlib for chart images
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime as dt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("⚠ matplotlib not installed. Email will not include chart images.")


def generate_chart_images(ta_data: dict):
    """Generate static candlestick chart PNGs for each stock."""
    if not HAS_MPL:
        return

    for key, stock in ta_data["stocks"].items():
        if "error" in stock:
            continue

        candles = stock["daily"]["candles"]
        if len(candles) < 10:
            continue

        dates = [dt.strptime(c["date"], "%Y-%m-%d") for c in candles[-60:]]  # Last 60 days
        opens = [c["open"] for c in candles[-60:]]
        highs = [c["high"] for c in candles[-60:]]
        lows = [c["low"] for c in candles[-60:]]
        closes = [c["close"] for c in candles[-60:]]

        fig, ax = plt.subplots(1, 1, figsize=(5.6, 2.0), dpi=144)
        fig.patch.set_facecolor('#161b22')
        ax.set_facecolor('#0a0e17')

        # Candlesticks as bar chart
        for i in range(len(dates)):
            color = '#3fb950' if closes[i] >= opens[i] else '#f85149'
            ax.plot([dates[i], dates[i]], [lows[i], highs[i]], color=color, linewidth=0.5)
            ax.plot([dates[i], dates[i]], [min(opens[i], closes[i]), max(opens[i], closes[i])],
                    color=color, linewidth=2.5)

        # EMA lines
        ema_short = stock["daily"].get("ema_short", [])
        ema_long = stock["daily"].get("ema_long", [])
        if ema_short:
            ema_dates = [dt.strptime(e["time"], "%Y-%m-%d") for e in ema_short[-60:]]
            ema_vals = [e["value"] for e in ema_short[-60:]]
            ax.plot(ema_dates, ema_vals, color='#58a6ff', linewidth=0.8, alpha=0.8)
        if ema_long:
            ema_dates = [dt.strptime(e["time"], "%Y-%m-%d") for e in ema_long[-60:]]
            ema_vals = [e["value"] for e in ema_long[-60:]]
            ax.plot(ema_dates, ema_vals, color='#d2a8ff', linewidth=0.8, alpha=0.8)

        # Stop loss line
        sl = stock["daily"].get("stop_loss", {}).get("stop_loss")
        if sl:
            ax.axhline(y=sl, color='#f0883e', linewidth=0.8, linestyle='--', alpha=0.7)

        # Support/Resistance
        for s in stock["daily"].get("support", [])[:2]:
            ax.axhline(y=s["price"], color='#3fb950', linewidth=0.5, linestyle=':', alpha=0.5)
        for r in stock["daily"].get("resistance", [])[:2]:
            ax.axhline(y=r["price"], color='#f85149', linewidth=0.5, linestyle=':', alpha=0.5)

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        ax.tick_params(colors='#8b949e', labelsize=7)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#21262d')
        ax.spines['left'].set_color('#21262d')

        plt.tight_layout(pad=0.3)
        out_path = CHART_DIR / f"{key}_mini.png"
        fig.savefig(out_path, facecolor=fig.get_facecolor(), bbox_inches='tight')
        plt.close(fig)
        print(f"  📸 {key}_mini.png")


def build_email_html(ta_data: dict) -> str:
    """Build email-safe inline-styled HTML."""
    date_str = ta_data["date"]
    try:
        date_formatted = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %b %Y")
    except Exception:
        date_formatted = date_str

    stocks = {k: v for k, v in ta_data["stocks"].items() if "error" not in v}
    if not stocks:
        return "<html><body>No stock data available today.</body></html>"

    dashboard_url = f"{SITE_URL}/dashboard/"
    report_url = f"{SITE_URL}/report/"
    charts_base = f"{SITE_URL}/assets/charts"

    # Count bulls/bears for subject line hint
    bulls = sum(1 for s in stocks.values() if s.get("trend") == "bull")
    bears = len(stocks) - bulls

    # Quick scan table rows
    table_rows = ""
    for key, s in stocks.items():
        price = s["current_price"]
        change = s.get("day_change_pct", 0)
        trend = s.get("trend", "unknown")
        change_color = "#3fb950" if change >= 0 else "#f85149"
        sign = "+" if change >= 0 else ""
        trend_badge_bg = "rgba(63,185,80,0.15)" if trend == "bull" else "rgba(248,81,73,0.15)"
        trend_badge_color = "#3fb950" if trend == "bull" else "#f85149"
        trend_text = "Bullish" if trend == "bull" else "Bearish"

        table_rows += f"""
        <tr style="border-bottom:1px solid #30363d;">
            <td style="padding:10px 12px;font-weight:600;color:#e1e4e8;font-size:14px;">{key}</td>
            <td style="padding:10px 12px;color:#e1e4e8;font-size:14px;text-align:right;">₹{price:,.2f}</td>
            <td style="padding:10px 12px;color:{change_color};font-size:14px;text-align:right;">{sign}{change:.1f}%</td>
            <td style="padding:10px 12px;text-align:center;">
                <span style="display:inline-block;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600;background:{trend_badge_bg};color:{trend_badge_color};">{trend_text}</span>
            </td>
        </tr>"""

    # Per-stock detail sections
    stock_sections = ""
    for key, s in stocks.items():
        price = s["current_price"]
        change = s.get("day_change_pct", 0)
        trend = s.get("trend", "unknown")
        sl = s["daily"].get("stop_loss", {})
        support = s["daily"].get("support", [])
        resistance = s["daily"].get("resistance", [])
        w52h = s.get("week52_high")
        w52l = s.get("week52_low")

        trend_emoji = "🐂" if trend == "bull" else "🐻"
        change_color = "#3fb950" if change >= 0 else "#f85149"
        header_bg = "#238636" if trend == "bull" else "#da3633"

        # 52W position
        w52_html = ""
        if w52h and w52l and w52h > w52l:
            pos = (price - w52l) / (w52h - w52l) * 100
            w52_html = f"""
            <tr>
                <td style="padding:6px 0;color:#8b949e;font-size:13px;">52W Range</td>
                <td style="padding:6px 0;font-size:13px;text-align:right;">
                    <span style="color:#a371f7;">₹{w52l:,.2f}</span> — <span style="color:#e3b341;">₹{w52h:,.2f}</span> ({pos:.0f}%)
                </td>
            </tr>"""

        support_text = ", ".join([f"₹{s['price']} ({s['strength']}x)" for s in support[:3]]) or "None"
        resistance_text = ", ".join([f"₹{r['price']} ({r['strength']}x)" for r in resistance[:3]]) or "None"

        chart_img_url = f"{charts_base}/{key}_mini.png"

        stock_sections += f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;border:1px solid #30363d;border-radius:8px;overflow:hidden;">
            <tr><td style="background:{header_bg};padding:10px 16px;">
                <span style="font-size:15px;font-weight:700;color:#fff;">{trend_emoji} {s['name']} ({key})</span>
                <span style="float:right;color:#fff;font-size:14px;">₹{price:,.2f} <span style="color:rgba(255,255,255,0.8);">({'+' if change >= 0 else ''}{change:.1f}%)</span></span>
            </td></tr>
            <tr><td style="padding:12px 16px;background:#161b22;">
                <img src="{chart_img_url}" alt="{key} chart" width="560" style="width:100%;max-width:560px;height:auto;border-radius:4px;margin-bottom:10px;" />
                <table width="100%" cellpadding="0" cellspacing="0" style="font-family:Arial,sans-serif;">
                    <tr>
                        <td style="padding:6px 0;color:#8b949e;font-size:13px;">Stop Loss</td>
                        <td style="padding:6px 0;font-size:13px;text-align:right;color:#f0883e;">₹{sl.get('stop_loss', 'N/A')} (Risk: {sl.get('risk_pct', 'N/A')}%)</td>
                    </tr>
                    <tr>
                        <td style="padding:6px 0;color:#8b949e;font-size:13px;">ATR(14)</td>
                        <td style="padding:6px 0;font-size:13px;text-align:right;">₹{sl.get('atr', 'N/A')}</td>
                    </tr>
                    {w52_html}
                    <tr>
                        <td style="padding:6px 0;color:#8b949e;font-size:13px;">Support</td>
                        <td style="padding:6px 0;font-size:13px;text-align:right;color:#3fb950;">{support_text}</td>
                    </tr>
                    <tr>
                        <td style="padding:6px 0;color:#8b949e;font-size:13px;">Resistance</td>
                        <td style="padding:6px 0;font-size:13px;text-align:right;color:#f85149;">{resistance_text}</td>
                    </tr>
                </table>
            </td></tr>
        </table>"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
</head>
<body style="margin:0;padding:0;background:#0d1117;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#0d1117;">
<tr><td align="center" style="padding:20px 10px;">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

    <!-- Header -->
    <tr><td style="background:linear-gradient(135deg,#1f6feb,#238636);padding:24px 20px;border-radius:8px 8px 0 0;">
        <h1 style="margin:0;font-size:22px;color:#fff;font-weight:700;">📊 Daily Stock Watchlist</h1>
        <p style="margin:6px 0 0;font-size:14px;color:rgba(255,255,255,0.85);">{date_formatted} · {bulls} Bullish · {bears} Bearish</p>
    </td></tr>

    <!-- View in browser -->
    <tr><td style="background:#161b22;padding:10px 20px;border-bottom:1px solid #30363d;">
        <a href="{dashboard_url}" style="color:#58a6ff;font-size:13px;text-decoration:none;">🔗 View interactive dashboard in browser →</a>
    </td></tr>

    <!-- Quick Scan Table -->
    <tr><td style="background:#161b22;padding:16px 20px;">
        <h2 style="margin:0 0 12px;font-size:15px;color:#e1e4e8;font-weight:600;">Quick Scan</h2>
        <table width="100%" cellpadding="0" cellspacing="0" style="font-family:Arial,sans-serif;">
            <tr style="border-bottom:2px solid #30363d;">
                <th style="padding:8px 12px;text-align:left;color:#8b949e;font-size:12px;font-weight:600;">Stock</th>
                <th style="padding:8px 12px;text-align:right;color:#8b949e;font-size:12px;font-weight:600;">Price</th>
                <th style="padding:8px 12px;text-align:right;color:#8b949e;font-size:12px;font-weight:600;">Change</th>
                <th style="padding:8px 12px;text-align:center;color:#8b949e;font-size:12px;font-weight:600;">Trend</th>
            </tr>
            {table_rows}
        </table>
    </td></tr>

    <!-- Per-Stock Sections -->
    <tr><td style="background:#0d1117;padding:16px 20px;">
        <h2 style="margin:0 0 12px;font-size:15px;color:#e1e4e8;font-weight:600;">Stock Details</h2>
        {stock_sections}
    </td></tr>

    <!-- Footer -->
    <tr><td style="background:#161b22;padding:16px 20px;border-radius:0 0 8px 8px;border-top:1px solid #30363d;">
        <p style="margin:0;font-size:12px;color:#6e7681;text-align:center;">
            Generated at {datetime.now(IST).strftime('%H:%M IST')} ·
            <a href="{dashboard_url}" style="color:#58a6ff;text-decoration:none;">Dashboard</a> ·
            <a href="{report_url}" style="color:#58a6ff;text-decoration:none;">Full Report</a>
        </p>
        <p style="margin:6px 0 0;font-size:11px;color:#484f58;text-align:center;">
            This is informational only — not financial advice. Data from Yahoo Finance.
        </p>
    </td></tr>

</table>
</td></tr>
</table>
</body>
</html>"""
    return html


def main():
    ta_path = DATA_DIR / "ta_results.json"
    if not ta_path.exists():
        print("❌ data/ta_results.json not found. Run ta_engine.py first.")
        sys.exit(1)

    with open(ta_path) as f:
        ta_data = json.load(f)

    print("📸 Generating chart images...")
    generate_chart_images(ta_data)

    print("📧 Generating email HTML...")
    email_html = build_email_html(ta_data)

    out_path = DATA_DIR / "email_body.html"
    with open(out_path, "w") as f:
        f.write(email_html)

    size_kb = len(email_html) / 1024
    print(f"✅ Email HTML → {out_path} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
