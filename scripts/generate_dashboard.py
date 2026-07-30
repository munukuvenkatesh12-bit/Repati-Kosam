"""
Generate self-contained interactive HTML dashboard with Lightweight Charts.
Input:  data/ta_results.json
Output: site/dashboard/index.html

The HTML file embeds all data as inline JSON — no API calls at page load.
Works from file:// and from GitHub Pages.
"""
import json
import sys
from datetime import datetime, timezone, timedelta

from config import DATA_DIR, SITE_DIR

IST = timezone(timedelta(hours=5, minutes=30))


def build_html(ta_data: dict) -> str:
    """Build the full dashboard HTML string."""
    date_str = ta_data["date"]
    stocks = ta_data["stocks"]

    # Filter out errored stocks
    valid_stocks = {k: v for k, v in stocks.items() if "error" not in v}
    if not valid_stocks:
        return "<html><body><h1>No stock data available</h1></body></html>"

    # Sort by key for consistent tab order
    stock_keys = list(valid_stocks.keys())

    # Serialize data for inline embedding
    chart_data_json = json.dumps(valid_stocks)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Stock Technical Dashboard — {date_str}</title>
<script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #0a0e17; color: #e1e4e8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; }}

.header {{ padding: 12px 20px; background: #161b22; border-bottom: 1px solid #21262d; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }}
.header h1 {{ font-size: 18px; font-weight: 600; }}
.header .date {{ color: #8b949e; font-size: 13px; }}

.tabs {{ display: flex; overflow-x: auto; background: #0d1117; border-bottom: 1px solid #21262d; -webkit-overflow-scrolling: touch; scrollbar-width: none; }}
.tabs::-webkit-scrollbar {{ display: none; }}
.tab {{ padding: 10px 16px; cursor: pointer; white-space: nowrap; font-size: 13px; border-bottom: 2px solid transparent; transition: all 0.2s; }}
.tab:hover {{ background: #161b22; }}
.tab.active {{ border-bottom-color: #1f6feb; background: #161b22; color: #58a6ff; }}
.tab .change {{ font-size: 11px; margin-left: 6px; }}
.tab .change.up {{ color: #3fb950; }}
.tab .change.down {{ color: #f85149; }}

.controls {{ display: flex; align-items: center; gap: 12px; padding: 8px 20px; background: #0d1117; border-bottom: 1px solid #21262d; flex-wrap: wrap; }}
.toggle-group {{ display: flex; border: 1px solid #30363d; border-radius: 6px; overflow: hidden; }}
.toggle-btn {{ padding: 4px 14px; font-size: 12px; cursor: pointer; background: transparent; color: #8b949e; border: none; }}
.toggle-btn.active {{ background: #238636; color: #fff; }}
.legend {{ display: flex; gap: 12px; font-size: 11px; color: #8b949e; flex-wrap: wrap; }}
.legend span {{ display: flex; align-items: center; gap: 4px; }}
.legend .dot {{ width: 10px; height: 3px; border-radius: 1px; }}

.main {{ display: flex; height: calc(100vh - 120px); }}
.chart-area {{ flex: 1; min-width: 0; padding: 8px; }}
#chart-container {{ width: 100%; height: 100%; }}

.info-panel {{ width: 280px; background: #161b22; border-left: 1px solid #21262d; overflow-y: auto; padding: 16px; }}
.info-section {{ margin-bottom: 16px; }}
.info-section h3 {{ font-size: 11px; text-transform: uppercase; color: #8b949e; margin-bottom: 8px; letter-spacing: 0.5px; }}
.info-row {{ display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 13px; }}
.info-row .label {{ color: #8b949e; }}
.price-big {{ font-size: 24px; font-weight: 700; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
.badge.bull {{ background: rgba(63,185,80,0.15); color: #3fb950; }}
.badge.bear {{ background: rgba(248,81,73,0.15); color: #f85149; }}

.w52-bar {{ width: 100%; height: 6px; background: #21262d; border-radius: 3px; margin: 6px 0; position: relative; }}
.w52-bar .fill {{ height: 100%; border-radius: 3px; background: linear-gradient(90deg, #a371f7, #e3b341); }}
.w52-bar .marker {{ position: absolute; top: -4px; width: 3px; height: 14px; background: #e1e4e8; border-radius: 2px; }}

.level-row {{ display: flex; justify-content: space-between; padding: 3px 0; font-size: 12px; }}
.level-row .touches {{ color: #8b949e; font-size: 11px; }}
.support-price {{ color: #3fb950; }}
.resistance-price {{ color: #f85149; }}

.zone-row {{ display: flex; align-items: center; gap: 6px; padding: 3px 0; font-size: 12px; }}
.zone-dot {{ width: 8px; height: 8px; border-radius: 50%; }}
.zone-dot.bull {{ background: #3fb950; }}
.zone-dot.bear {{ background: #f85149; }}

@media (max-width: 900px) {{
    .main {{ flex-direction: column; height: auto; }}
    .chart-area {{ height: 60vh; min-height: 300px; }}
    .info-panel {{ width: 100%; border-left: none; border-top: 1px solid #21262d; max-height: 40vh; }}
}}
@media (max-width: 600px) {{
    .tab {{ padding: 8px 12px; font-size: 12px; }}
    .info-panel {{ padding: 12px; }}
    .price-big {{ font-size: 20px; }}
}}
</style>
</head>
<body>

<div class="header">
    <h1>Stock Technical Dashboard</h1>
    <span class="date">Updated {datetime.now(IST).strftime('%d %b %Y, %H:%M IST')}</span>
</div>

<div class="tabs" id="stock-tabs"></div>

<div class="controls">
    <div class="toggle-group">
        <button class="toggle-btn active" data-tf="daily" onclick="setTimeframe('daily')">Daily</button>
        <button class="toggle-btn" data-tf="weekly" onclick="setTimeframe('weekly')">Weekly</button>
    </div>
    <div class="legend">
        <span><span class="dot" style="background:#58a6ff"></span>EMA 20</span>
        <span><span class="dot" style="background:#d2a8ff"></span>EMA 50</span>
        <span><span class="dot" style="background:#f0883e"></span>Stop Loss</span>
        <span><span class="dot" style="background:#3fb950"></span>Support</span>
        <span><span class="dot" style="background:#f85149"></span>Resistance</span>
        <span><span class="dot" style="background:#e3b341"></span>52W High</span>
        <span><span class="dot" style="background:#a371f7"></span>52W Low</span>
    </div>
</div>

<div class="main">
    <div class="chart-area"><div id="chart-container"></div></div>
    <div class="info-panel" id="info-panel"></div>
</div>

<script>
// ── Embedded Data ──
const ALL_DATA = {chart_data_json};
const STOCK_KEYS = {json.dumps(stock_keys)};

let currentStock = STOCK_KEYS[0];
let currentTimeframe = 'daily';
let chart = null;
let candleSeries = null;
let volumeSeries = null;
let emaShortSeries = null;
let emaLongSeries = null;

// ── Tabs ──
function buildTabs() {{
    const container = document.getElementById('stock-tabs');
    container.innerHTML = STOCK_KEYS.map(key => {{
        const d = ALL_DATA[key];
        const pct = d.day_change_pct || 0;
        const cls = pct >= 0 ? 'up' : 'down';
        const sign = pct >= 0 ? '+' : '';
        return `<div class="tab ${{key === currentStock ? 'active' : ''}}" onclick="selectStock('${{key}}')">
            ${{key}}<span class="change ${{cls}}">${{sign}}${{pct.toFixed(1)}}%</span>
        </div>`;
    }}).join('');
}}

function selectStock(key) {{
    currentStock = key;
    buildTabs();
    renderChart();
    renderInfoPanel();
}}

function setTimeframe(tf) {{
    currentTimeframe = tf;
    document.querySelectorAll('.toggle-btn').forEach(b => b.classList.toggle('active', b.dataset.tf === tf));
    renderChart();
    renderInfoPanel();
}}

// ── Chart ──
function renderChart() {{
    const container = document.getElementById('chart-container');
    container.innerHTML = '';

    chart = LightweightCharts.createChart(container, {{
        width: container.clientWidth,
        height: container.clientHeight,
        layout: {{ background: {{ type: 'solid', color: '#0a0e17' }}, textColor: '#8b949e', fontSize: 11 }},
        grid: {{ vertLines: {{ color: '#1c2333' }}, horzLines: {{ color: '#1c2333' }} }},
        crosshair: {{ mode: 0 }},
        rightPriceScale: {{ borderColor: '#21262d' }},
        timeScale: {{ borderColor: '#21262d', timeVisible: false }},
    }});

    const stock = ALL_DATA[currentStock];
    const tf = stock[currentTimeframe];
    if (!tf || !tf.candles || tf.candles.length === 0) return;

    // Candlestick
    candleSeries = chart.addCandlestickSeries({{
        upColor: '#3fb950', downColor: '#f85149', borderUpColor: '#3fb950', borderDownColor: '#f85149',
        wickUpColor: '#3fb950', wickDownColor: '#f85149',
    }});
    candleSeries.setData(tf.candles.map(c => ({{ time: c.date, open: c.open, high: c.high, low: c.low, close: c.close }})));

    // Volume
    volumeSeries = chart.addHistogramSeries({{
        priceFormat: {{ type: 'volume' }}, priceScaleId: 'vol',
    }});
    chart.priceScale('vol').applyOptions({{ scaleMargins: {{ top: 0.85, bottom: 0 }} }});
    volumeSeries.setData(tf.candles.map(c => ({{
        time: c.date, value: c.volume, color: c.close >= c.open ? 'rgba(63,185,80,0.3)' : 'rgba(248,81,73,0.3)',
    }})));

    // EMA lines
    if (tf.ema_short && tf.ema_short.length > 0) {{
        emaShortSeries = chart.addLineSeries({{ color: '#58a6ff', lineWidth: 1, priceLineVisible: false }});
        emaShortSeries.setData(tf.ema_short);
    }}
    if (tf.ema_long && tf.ema_long.length > 0) {{
        emaLongSeries = chart.addLineSeries({{ color: '#d2a8ff', lineWidth: 1, priceLineVisible: false }});
        emaLongSeries.setData(tf.ema_long);
    }}

    // Stop Loss line
    if (tf.stop_loss && tf.stop_loss.stop_loss) {{
        candleSeries.createPriceLine({{
            price: tf.stop_loss.stop_loss, color: '#f0883e', lineWidth: 2, lineStyle: 1,
            axisLabelVisible: true, title: 'SL',
        }});
    }}

    // Support lines
    (tf.support || []).forEach(s => {{
        candleSeries.createPriceLine({{
            price: s.price, color: '#3fb950', lineWidth: 1, lineStyle: 1,
            axisLabelVisible: false, title: '',
        }});
    }});

    // Resistance lines
    (tf.resistance || []).forEach(r => {{
        candleSeries.createPriceLine({{
            price: r.price, color: '#f85149', lineWidth: 1, lineStyle: 1,
            axisLabelVisible: false, title: '',
        }});
    }});

    // 52W High/Low
    if (stock.week52_high) {{
        candleSeries.createPriceLine({{
            price: stock.week52_high, color: '#e3b341', lineWidth: 1, lineStyle: 2,
            axisLabelVisible: true, title: '52W H',
        }});
    }}
    if (stock.week52_low) {{
        candleSeries.createPriceLine({{
            price: stock.week52_low, color: '#a371f7', lineWidth: 1, lineStyle: 2,
            axisLabelVisible: true, title: '52W L',
        }});
    }}

    // Bull/Bear zone markers
    (tf.bull_bear_runs || []).forEach((zone, i) => {{
        if (i === 0) return;
        candleSeries.setMarkers([...(candleSeries.markers?.() || []), {{
            time: zone.start, position: zone.type === 'bull' ? 'belowBar' : 'aboveBar',
            color: zone.type === 'bull' ? '#3fb950' : '#f85149',
            shape: zone.type === 'bull' ? 'arrowUp' : 'arrowDown',
            text: zone.type === 'bull' ? 'Bull' : 'Bear',
        }}]);
    }});

    // Set markers properly
    const markers = [];
    (tf.bull_bear_runs || []).forEach((zone, i) => {{
        if (i === 0) return;
        markers.push({{
            time: zone.start, position: zone.type === 'bull' ? 'belowBar' : 'aboveBar',
            color: zone.type === 'bull' ? '#3fb950' : '#f85149',
            shape: zone.type === 'bull' ? 'arrowUp' : 'arrowDown',
            text: zone.type === 'bull' ? 'Bull' : 'Bear',
        }});
    }});
    if (markers.length) candleSeries.setMarkers(markers.sort((a, b) => a.time > b.time ? 1 : -1));

    chart.timeScale().fitContent();

    // Resize handler
    const ro = new ResizeObserver(() => {{
        chart.applyOptions({{ width: container.clientWidth, height: container.clientHeight }});
    }});
    ro.observe(container);
}}

// ── Info Panel ──
function renderInfoPanel() {{
    const stock = ALL_DATA[currentStock];
    const tf = stock[currentTimeframe];
    const panel = document.getElementById('info-panel');

    const price = stock.current_price;
    const change = stock.day_change || 0;
    const changePct = stock.day_change_pct || 0;
    const changeColor = change >= 0 ? '#3fb950' : '#f85149';
    const changeSign = change >= 0 ? '+' : '';
    const trend = stock.trend || 'unknown';

    let w52Html = '';
    if (stock.week52_high && stock.week52_low) {{
        const range = stock.week52_high - stock.week52_low;
        const pos = range > 0 ? ((price - stock.week52_low) / range * 100) : 50;
        const fromHigh = ((stock.week52_high - price) / stock.week52_high * 100).toFixed(1);
        const fromLow = ((price - stock.week52_low) / stock.week52_low * 100).toFixed(1);
        w52Html = `
            <div class="info-section">
                <h3>52-Week Range</h3>
                <div class="info-row"><span class="label">High</span><span style="color:#e3b341">₹${{stock.week52_high.toLocaleString()}}</span></div>
                <div class="info-row"><span class="label">Low</span><span style="color:#a371f7">₹${{stock.week52_low.toLocaleString()}}</span></div>
                <div class="w52-bar">
                    <div class="fill" style="width:${{pos}}%"></div>
                    <div class="marker" style="left:${{pos}}%"></div>
                </div>
                <div class="info-row"><span class="label">From High</span><span>-${{fromHigh}}%</span></div>
                <div class="info-row"><span class="label">From Low</span><span>+${{fromLow}}%</span></div>
            </div>`;
    }}

    const sl = tf.stop_loss || {{}};
    const slHtml = sl.stop_loss ? `
        <div class="info-section">
            <h3>Stop Loss</h3>
            <div class="info-row"><span class="label">Level</span><span style="color:#f0883e">₹${{sl.stop_loss}}</span></div>
            <div class="info-row"><span class="label">ATR(14)</span><span>₹${{sl.atr}}</span></div>
            <div class="info-row"><span class="label">Risk</span><span>${{sl.risk_pct}}%</span></div>
            <div class="info-row"><span class="label">Method</span><span style="font-size:11px;color:#8b949e">${{sl.method}}</span></div>
        </div>` : '';

    const supportHtml = (tf.support || []).map(s => `
        <div class="level-row"><span class="support-price">₹${{s.price}}</span><span class="touches">${{s.strength}}x touched</span></div>
    `).join('') || '<div style="color:#6e7681;font-size:12px">None detected</div>';

    const resistanceHtml = (tf.resistance || []).map(r => `
        <div class="level-row"><span class="resistance-price">₹${{r.price}}</span><span class="touches">${{r.strength}}x touched</span></div>
    `).join('') || '<div style="color:#6e7681;font-size:12px">None detected</div>';

    const zonesHtml = (tf.bull_bear_runs || []).slice(-4).map(z => `
        <div class="zone-row">
            <div class="zone-dot ${{z.type}}"></div>
            <span>${{z.type === 'bull' ? 'Bull' : 'Bear'}}: ${{z.start}} → ${{z.end}}</span>
        </div>
    `).join('');

    panel.innerHTML = `
        <div class="info-section">
            <h3>${{stock.name}}</h3>
            <div class="price-big" style="color:${{changeColor}}">₹${{price.toLocaleString()}}</div>
            <div style="color:${{changeColor}};font-size:13px;margin-top:4px">${{changeSign}}${{change}} (${{changeSign}}${{changePct}}%)</div>
            <div style="margin-top:8px"><span class="badge ${{trend}}">${{trend === 'bull' ? '🐂 Bullish' : '🐻 Bearish'}}</span></div>
        </div>
        ${{w52Html}}
        ${{slHtml}}
        <div class="info-section"><h3>Support Levels</h3>${{supportHtml}}</div>
        <div class="info-section"><h3>Resistance Levels</h3>${{resistanceHtml}}</div>
        <div class="info-section"><h3>Trend Zones</h3>${{zonesHtml}}</div>
    `;
}}

// ── Init ──
buildTabs();
renderChart();
renderInfoPanel();
</script>
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

    html = build_html(ta_data)

    out_dir = SITE_DIR / "dashboard"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "index.html"
    with open(out_path, "w") as f:
        f.write(html)

    size_kb = len(html) / 1024
    print(f"✅ Dashboard generated → {out_path} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
