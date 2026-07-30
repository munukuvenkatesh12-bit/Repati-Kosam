#!/usr/bin/env python3
"""Daily Stock Watchlist Report Generator - July 30, 2026"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether, HRFlowable
)
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.lib import colors

# ─── COLORS ───
NAVY = HexColor('#1B2A4A')
DARK_NAVY = HexColor('#0F1B33')
LIGHT_GRAY = HexColor('#F5F6FA')
MEDIUM_GRAY = HexColor('#E0E3EB')
GREEN = HexColor('#27AE60')
AMBER = HexColor('#F39C12')
RED = HexColor('#E74C3C')
BLUE_ACCENT = HexColor('#3498DB')
WHITE = white
TEXT_DARK = HexColor('#2C3E50')
TEXT_LIGHT = HexColor('#7F8C8D')
BORDER_COLOR = HexColor('#D5D8DC')
COVER_BG = HexColor('#1B2A4A')
SECTION_BG = HexColor('#EBF5FB')

# ─── STOCK DATA ───
stocks = [
    {
        "name": "Vodafone Idea Limited",
        "ticker": "IDEA",
        "isin": "INE669E01016",
        "verdict": "Neutral",
        "verdict_color": AMBER,
        "verdict_reason": "AGR relief boosted reported profit, but underlying operations remain weak with negative net worth and heavy debt",
        "one_year_change": 79.1,
        "price": 12.95,
        "pe": 4.07,
        "pb": -3.96,
        "financials": [
            ("Revenue (FY26)", "Rs 44,789 Cr (+3.1% YoY)"),
            ("Net Profit (FY26)", "Rs 34,552 Cr (includes Rs 55,622 Cr exceptional AGR gain)"),
            ("5-Year Sales CAGR", "1.36% (poor)"),
            ("ARPU (Q4 FY26)", "Rs 190 (up 8.3% YoY from Rs 175)"),
        ],
        "roe_de": "ROE: 0.39 (weak) | D/E: Negative (negative net worth) | Bank debt reduced to Rs 726 Cr from Rs 2,326 Cr",
        "pe_hist": "P/E: 4.07 (depressed due to exceptional gain) | P/B: -3.96 (negative book value)",
        "sentiment": "Mixed. AGR dues reduction of Rs 55,622 Cr provided a one-time boost, but underlying business remains loss-making. Stock gained ~79% in one year on AGR hopes and tariff hikes.",
        "tailwinds": "AGR relief, tariff hikes lifting ARPU, 4G-to-5G transition underway, government stake provides implicit support",
        "headwinds": "Negative net worth, continued subscriber losses to Jio/Airtel, massive capex needed for 5G, low interest coverage, competitive pricing pressure",
        "governance": "Government of India holds ~33% stake; recent AGR order significantly reduced liabilities; company raised capital via FPO in 2024",
        "analyst_consensus": "Consensus: Sell | 4 Buy, 6 Hold, 11 Sell (out of 21 analysts)",
        "analyst_pct": "Buy: 19% | Hold: 29% | Sell: 52%",
        "target_prices": "Average: Rs 7.35 | Low: Rs 2.30 | High: Rs 15.30",
        "risks": "Negative net worth, massive debt overhang, intense competition from Jio and Airtel, execution risk on 5G rollout, regulatory uncertainty",
        "volatility": "High beta stock. 52-week range Rs 6.12 to Rs 15.34 — a 150% spread. Significantly more volatile than Nifty 50.",
        "plain_english": "Vodafone Idea got a huge one-time boost because the Supreme Court reduced what it owed the government (called AGR dues) by about Rs 55,600 crore. That made its yearly profit look great on paper, but the actual phone business is still struggling — it's losing customers to Jio and Airtel, and the company's debts still far exceed its assets. The stock has rallied ~79% this year on hopes, but analysts mostly say 'sell' because the fundamentals remain fragile."
    },
    {
        "name": "Aurobindo Pharma Limited",
        "ticker": "AUROPHARMA",
        "isin": "INE406A01037",
        "verdict": "Positive",
        "verdict_color": GREEN,
        "verdict_reason": "Strong US generics pipeline, FTC-approved Lannett acquisition, consistent growth, and broad analyst Buy consensus",
        "one_year_change": 36.7,
        "price": 1548.4,
        "pe": 18.6,
        "pb": 2.5,
        "financials": [
            ("Revenue (FY25)", "Rs 31,720 Cr (+9.4% YoY)"),
            ("Net Profit (FY25)", "Rs 3,490 Cr (+9.9% YoY)"),
            ("Profit Margin", "11% (stable)"),
            ("EPS", "Rs 59.81 (up from Rs 54.15)"),
        ],
        "roe_de": "ROE: 10.8% (3-year avg, below 15% benchmark) | Debt levels manageable vs peers in pharma sector",
        "pe_hist": "P/E: 18.6x (38% discount to sector median of 33.4x) | Trading below historical average",
        "sentiment": "Positive. Strong US market presence, Lannett acquisition (FTC approved, $250M) boosts complex generics portfolio. Stock up ~37% in a year.",
        "tailwinds": "US generics market expansion, Lannett acquisition adding complex generics capacity, biosimilar pipeline, growing specialty portfolio",
        "headwinds": "US FDA inspection risks, pricing pressure in US generics market, forex sensitivity, below-benchmark ROE",
        "governance": "Stable promoter holding; FTC-approved Lannett acquisition deal closing June 2026; HSBC reiterated Buy with Rs 1,580 target",
        "analyst_consensus": "Consensus: Buy | 21 Buy, 1 Hold, 4 Sell (out of 26 analysts)",
        "analyst_pct": "Buy: 81% | Hold: 4% | Sell: 15%",
        "target_prices": "Average: Rs 1,519 | Low: Rs 1,020 | High: Rs 1,662",
        "risks": "FDA regulatory actions, US drug pricing reforms, currency fluctuation, supply chain disruptions, patent challenges",
        "volatility": "Moderate. 52-week range Rs 1,016 to Rs 1,637. Beta near market average. Less volatile than small/mid-cap peers.",
        "plain_english": "Aurobindo makes generic medicines, especially for the US market. Business is growing steadily — revenue and profit both rose about 10% last year. The company recently got approval to buy a US company called Lannett for $250 million, which will help it make more complex medicines. Most analysts (81%) recommend buying the stock, and it's trading at a discount compared to similar pharma companies. The main worry is that the US drug regulator (FDA) could flag issues at their factories."
    },
    {
        "name": "NCC Limited",
        "ticker": "NCC",
        "isin": "INE868B01028",
        "verdict": "Neutral",
        "verdict_color": AMBER,
        "verdict_reason": "Record order book provides visibility, but NHAI debarment and muted stock performance weigh on sentiment",
        "one_year_change": -34.0,
        "price": 144.3,
        "pe": 15.9,
        "pb": 1.2,
        "financials": [
            ("Revenue (FY26)", "~Rs 16,850 Cr (+14.1% YoY)"),
            ("PAT (FY26)", "Rs 680 Cr (+32.6% YoY)"),
            ("Profit Margin", "3.2% (down from 3.7%)"),
            ("Order Book", "Rs 83,004 Cr (+16% YoY, Book-to-bill 4x)"),
        ],
        "roe_de": "ROE: 11.19% | D/E: 0.22 (low leverage) | Net debt: Rs 2,154 Cr",
        "pe_hist": "P/E: 15.9x | P/B: 1.2x | Reasonable valuation for infrastructure sector",
        "sentiment": "Mixed to negative. Despite record order book (Rs 83,004 Cr), stock has fallen 34% in one year. NHAI debarment for 2 years (effective Feb 2026) is a significant overhang.",
        "tailwinds": "Record order book with 4x book-to-bill, government infrastructure push, diversified order mix, low debt",
        "headwinds": "NHAI 2-year debarment (no new highway tenders), margin compression, working capital challenges in infra sector",
        "governance": "NHAI debarment of NCC and step-down subsidiary for 2 years effective Feb 17, 2026. Fresh order wins of Rs 535 Cr in June 2026 (non-NHAI).",
        "analyst_consensus": "Consensus: Buy (among covering analysts) | 12 analysts with average Buy rating",
        "analyst_pct": "Buy: ~60% | Hold: ~25% | Sell: ~15%",
        "target_prices": "Average: Rs 207 | Low: Rs 162 | High: Rs 269",
        "risks": "NHAI debarment limiting highway order wins, thin margins typical of EPC sector, execution delays, working capital intensity, competitive bidding pressure",
        "volatility": "Moderate-high. 52-week range Rs 130 to Rs 232. Stock down 34% in 1 year — underperforming Nifty 50 significantly.",
        "plain_english": "NCC builds roads, bridges, and buildings. Their pipeline of future work (order book) hit a record Rs 83,000 crore, which means they have 4 years' worth of work lined up. Profit also grew 33%. However, the stock has fallen 34% because India's highway authority (NHAI) banned NCC from bidding on new highway projects for 2 years. That's a big deal since highways are a major revenue source. The company is pivoting to other infrastructure segments to compensate."
    },
    {
        "name": "Hindustan Construction Company Ltd",
        "ticker": "HCC",
        "isin": "INE549A01026",
        "verdict": "Neutral",
        "verdict_color": AMBER,
        "verdict_reason": "Debt reduction progress is encouraging, but revenue decline and high PE suggest caution",
        "one_year_change": -15.0,
        "price": 22.0,
        "pe": 55.0,
        "pb": 2.46,
        "financials": [
            ("Revenue (FY26)", "Rs 3,970 Cr (-29.2% YoY)"),
            ("Net Profit (FY26)", "Rs 166 Cr (+47% YoY)"),
            ("Standalone PAT", "Rs 206 Cr"),
            ("Debt Reduction", "38% YoY to Rs 1,995 Cr"),
        ],
        "roe_de": "ROE: 10.91% | D/E: 0.48 (improved, was higher) | Total debt reduced 38% YoY to Rs 1,995 Cr",
        "pe_hist": "P/E: 55.0x (expensive) | P/B: 2.46x | Valuation stretched relative to earnings",
        "sentiment": "Cautiously positive. Profit improved 47% and debt fell 38%, but revenue dropped 29%. Market cap Rs 5,679 Cr. Rights issue of Rs 1,000 Cr subscribed at 200%.",
        "tailwinds": "Debt reduction momentum (38% YoY), improved profitability, successful Rs 1,000 Cr rights issue, government infra push",
        "headwinds": "Sharp revenue decline (-29%), high PE multiple, execution challenges, legacy debt overhang still significant",
        "governance": "100th AGM scheduled Aug 18, 2026. Rs 1,000 Cr rights issue subscribed at 200% — strong promoter/investor confidence signal.",
        "analyst_consensus": "Limited coverage. Target around Rs 30-35 (bull case)",
        "analyst_pct": "Buy: ~40% | Hold: ~40% | Sell: ~20% (limited coverage)",
        "target_prices": "Average: Rs 30 | Low: Rs 20 | High: Rs 35",
        "risks": "Revenue volatility, execution delays on large projects, residual debt burden, thin analyst coverage, working capital stress",
        "volatility": "High. 52-week range Rs 13.65 to Rs 28.50. Small-cap characteristics with wide price swings.",
        "plain_english": "HCC is an old infrastructure company (100 years!) that builds dams, tunnels, and highways. They've been working hard to pay down debt — cutting it by 38% this year, which is good. Profit also jumped 47%. But there's a catch: their revenue (the money coming in from projects) dropped nearly 30%, which means they're completing old projects faster than winning new ones. The stock is thinly covered by analysts, so information is limited."
    },
    {
        "name": "Adani Green Energy Limited",
        "ticker": "ADANIGREEN",
        "isin": "INE364U01010",
        "verdict": "Positive",
        "verdict_color": GREEN,
        "verdict_reason": "Strong revenue growth, 91% EBITDA margins, aggressive capacity expansion; debt is high but manageable for growth stage",
        "one_year_change": 56.6,
        "price": 1395.1,
        "pe": 153.2,
        "pb": 12.0,
        "financials": [
            ("Revenue (FY26)", "Rs 13,820 Cr (+22% YoY)"),
            ("Net Income (FY26)", "Rs 1,650 Cr (+25% YoY)"),
            ("EBITDA Margin", "91.2%"),
            ("Revenue CAGR (3yr fwd)", "31% projected"),
        ],
        "roe_de": "ROE: 6.7% | D/E: ~7.6x (very high, growth-stage) | Net debt Rs 95,621 Cr (up from Rs 72,829 Cr YoY)",
        "pe_hist": "P/E: 153.2x (premium, down from 5-yr avg of 288x) | Forward P/E: ~79.5x | Sector avg: 23.3x",
        "sentiment": "Bullish. Stock up 57% in one year, hit 52-week high of Rs 1,631. Brokerage raised target to Rs 1,800. Strong buy consensus.",
        "tailwinds": "India's renewable energy push, 30% EBITDA CAGR expected over 5 years, capacity scale-up, 91% EBITDA margin, policy support",
        "headwinds": "Very high debt (Rs 95,621 Cr), elevated PE multiple, interest rate sensitivity, grid connectivity delays, Adani group governance concerns",
        "governance": "Part of Adani Group. Aggressive capacity expansion. Debt-to-capital ratio at 95.3% — high but typical for renewable energy developers.",
        "analyst_consensus": "Consensus: Strong Buy | 8 analysts with Buy rating",
        "analyst_pct": "Buy: ~75% | Hold: ~15% | Sell: ~10%",
        "target_prices": "Average: Rs 1,440 | Low: Rs 864 | High: Rs 1,800",
        "risks": "High leverage (D/E ~7.6x), grid connectivity delays, regulatory changes, Adani group reputational risk, rising borrowing costs",
        "volatility": "High. 52-week range Rs 767 to Rs 1,631. Large price swings — stock more than doubled from its low.",
        "plain_english": "Adani Green runs solar and wind power plants. It's growing fast — revenue up 22% and it keeps over 91 paise of every rupee earned as operating profit, which is remarkable. The stock has rallied 57% this year. The catch is that the company has borrowed heavily (about Rs 95,600 crore) to build all these plants. That's normal for this kind of business, but if interest rates rise or projects get delayed, it could squeeze them. Most analysts are bullish because India needs a lot more clean energy."
    },
    {
        "name": "Adani Power Limited",
        "ticker": "ADANIPOWER",
        "isin": "INE814H01029",
        "verdict": "Positive",
        "verdict_color": GREEN,
        "verdict_reason": "Record EBITDA, strong ROE of 25%, massive capacity expansion plan backed by internal cash flows and global brokerage upgrades",
        "one_year_change": 84.0,
        "price": 213.7,
        "pe": 38.0,
        "pb": 7.87,
        "financials": [
            ("Revenue (FY26)", "Rs 18,902 Cr (vs Rs 14,109 Cr YoY)"),
            ("Net Profit (FY26)", "Rs 4,806 Cr (+45% YoY)"),
            ("Revenue CAGR", "118.19% (far above industry median 17.6%)"),
            ("Q1 FY27", "Record EBITDA, revenue up 28% YoY"),
        ],
        "roe_de": "ROE: 24.74% (45% above 10-yr median of 17%) | Net debt/EBITDA target: below 3x | QIP of Rs 15,000 Cr approved",
        "pe_hist": "P/E: 38.0x | P/B: 7.87x | Premium valuation reflecting growth expectations",
        "sentiment": "Bullish. Stock up 84% in one year. 3 global brokerages (Morgan Stanley, Cantor, Bernstein) gave Overweight/Outperform ratings post Q1 FY27 results.",
        "tailwinds": "45 GW capacity target by 2031 (up from 42 GW), Rs 2 lakh crore capex funded internally, record EBITDA, power demand growth",
        "headwinds": "High PE valuation, coal price volatility, regulatory risk on tariffs, large capex execution risk, environmental concerns",
        "governance": "Board approved Rs 15,000 Cr QIP. Capacity expansion to 45 GW on schedule. 7,720 MW under construction.",
        "analyst_consensus": "Consensus: Overweight/Buy | Morgan Stanley: Rs 275, Cantor: Rs 266, Bernstein: Rs 220",
        "analyst_pct": "Buy: ~70% | Hold: ~20% | Sell: ~10%",
        "target_prices": "Average: Rs 248 | Low: Rs 220 | High: Rs 275",
        "risks": "Coal price spikes, regulatory changes on power tariffs, execution risk on massive capex plan, environmental compliance, Adani group governance",
        "volatility": "High. 52-week range Rs 110.45 to Rs 254.20. Stock nearly doubled from its low — high momentum but also high risk.",
        "plain_english": "Adani Power runs coal and thermal power plants. The company is on a tear — profit jumped 45% and it just posted record operating earnings. It's planning to nearly triple its power generation capacity to 45 GW by 2031, spending about Rs 2 lakh crore mostly from its own earnings. Three major global investment banks recently said 'buy.' The stock has rallied 84% this year. The risk is that this ambitious expansion depends on coal prices staying reasonable and government regulations remaining favorable."
    },
    {
        "name": "Waaree Energies Limited",
        "ticker": "WAAREEENER",
        "isin": "INE377N01017",
        "verdict": "Positive",
        "verdict_color": GREEN,
        "verdict_reason": "India's largest solar module maker, 45% earnings CAGR, strong order book; US tariff risk mitigated by local manufacturing",
        "one_year_change": -15.1,
        "price": 2702.0,
        "pe": 27.7,
        "pb": 7.0,
        "financials": [
            ("Revenue (FY26)", "Rs 26,537 Cr"),
            ("Net Profit (FY26)", "Rs 3,884 Cr"),
            ("Earnings Growth (1yr)", "71.3%"),
            ("5-Year Earnings CAGR", "45.2%"),
        ],
        "roe_de": "ROE: ~27% (strong) | D/E: Low (~0.12) | Long-term debt Rs 310 Cr only",
        "pe_hist": "P/E: 27.7x (25% below 10-yr median of 36.9x) | Reasonable for growth profile",
        "sentiment": "Mixed-positive. Downgraded from Buy to Hold by some analysts, but Emkay maintains Buy with Rs 4,260 target (57% upside). US tariff risk (126% CVD) is key concern.",
        "tailwinds": "India solar push, 5.15 GWh battery storage production started, US manufacturing expansion, strong earnings growth",
        "headwinds": "US 126% CVD on Indian solar imports (final ruling July 2026), stock down 15% from highs, rating downgrade by some brokerages",
        "governance": "Secured 212 MW solar module order. Subsidiary began BESS production at 5.15 GWh capacity (above planned 3.5 GWh).",
        "analyst_consensus": "Consensus: Buy | 9 Buy, 0 Hold, 5 Sell (13 analysts)",
        "analyst_pct": "Buy: 69% | Hold: 0% | Sell: 31%",
        "target_prices": "Average: Rs 3,494 | Low: Rs 2,109 | High: Rs 4,400",
        "risks": "US countervailing duty (126% CVD), solar module price volatility, technology obsolescence risk, project execution, competition from Chinese manufacturers",
        "volatility": "High. 52-week range Rs 2,403 to Rs 3,865. Down 30% from 52-week high. High growth stock with high volatility.",
        "plain_english": "Waaree is India's biggest solar panel maker. Their profits shot up 71% last year, and they've grown earnings at 45% annually over five years — very impressive. They've also started making battery storage systems. The big worry right now is that the US government might slap a 126% tax on solar panels imported from India, which could hurt exports. But Waaree is building factories in the US to get around this. Most analysts still say 'buy,' with targets suggesting 30-60% upside from current prices."
    },
    {
        "name": "Billionbrains Garage Ventures Ltd",
        "ticker": "GROWW",
        "isin": "INE0HOQ01053",
        "verdict": "Neutral",
        "verdict_color": AMBER,
        "verdict_reason": "Dominant fintech platform with strong growth, but expensive valuation (PE 52x) and nascent public market track record",
        "one_year_change": 81.0,
        "price": 202.5,
        "pe": 52.4,
        "pb": 13.25,
        "financials": [
            ("Revenue (FY26)", "Rs 5,242 Cr"),
            ("Net Profit (FY26)", "Rs 2,440 Cr"),
            ("Q4 FY26 PAT", "Rs 686 Cr (+122% YoY)"),
            ("Revenue Growth (3yr fwd)", "26.9% CAGR projected"),
        ],
        "roe_de": "ROE: 50.03% (exceptional) | D/E: Minimal (tech platform, asset-light model)",
        "pe_hist": "P/E: 52.4x (vs sector avg 28.6x — 83% premium) | P/B: 13.25x (sector avg 4.83x)",
        "sentiment": "Positive but expensive. Stock up 81% since IPO (listed Nov 2025 at Rs 112). India's largest digital investment platform by active users.",
        "tailwinds": "India's financialization trend, largest digital investment platform, 122% Q4 profit growth, asset-light model, massive user base",
        "headwinds": "Expensive valuation (PE 52x), regulatory risk from SEBI, limited public track record (listed Nov 2025), competition from Zerodha/Angel",
        "governance": "Listed Nov 2025 via IPO at Rs 95-100 band. IPO subscribed 17.6x. Currently trading at Rs 203 — 103% above issue price.",
        "analyst_consensus": "Consensus: Hold | Limited analyst coverage given recent listing",
        "analyst_pct": "Buy: ~35% | Hold: ~45% | Sell: ~20% (estimated, limited coverage)",
        "target_prices": "Limited formal targets available. Stock near Rs 203 vs IPO price Rs 112.",
        "risks": "SEBI regulatory changes on discount broking, valuation premium compression, competition, customer acquisition cost inflation, market downturn reducing trading volumes",
        "volatility": "Moderate-high. 52-week range Rs 112 to Rs 227. Recently listed, so limited history. Trading at 81% above IPO price.",
        "plain_english": "Groww (officially Billionbrains Garage Ventures) is India's most popular investment app — think of it as the platform millions of Indians use to buy stocks, mutual funds, and more on their phones. The company is growing incredibly fast, with profits more than doubling. It listed on the stock exchange in November 2025 and the stock has nearly doubled since. The concern is that at 52 times earnings, you're paying a premium price. If India's stock market activity slows down or regulators change rules, the stock could correct."
    },
    {
        "name": "Digilogic Systems Ltd",
        "ticker": "544684",
        "isin": "INE1OOT01028",
        "verdict": "Positive",
        "verdict_color": GREEN,
        "verdict_reason": "Strong defence sector tailwinds, 34% profit growth, near-zero debt, attractive PE vs peers, capacity expansion underway",
        "one_year_change": 60.0,
        "price": 119.0,
        "pe": 32.8,
        "pb": 5.0,
        "financials": [
            ("Revenue (FY26)", "Rs 77.4 Cr (+8.4% YoY)"),
            ("PAT (FY26)", "Rs 10.43 Cr (+33.8% YoY)"),
            ("EBITDA (FY26)", "Rs 15.18 Cr (+16.5% YoY)"),
            ("EBITDA Margin", "19.6% (+152 bps YoY)"),
        ],
        "roe_de": "ROE: ~22% (strong for micro-cap) | D/E: 0.04 (near zero debt, down from 0.40 in FY25)",
        "pe_hist": "P/E: 32.8x (65% discount to defence sector median of 93.6x) | Deeply undervalued vs peers",
        "sentiment": "Positive. Defence sector darling. New Rs 12.98 Cr order from Defence PSU. IPO listed Jan 2026 on BSE. Capacity expansion of Rs 51.74 Cr announced.",
        "tailwinds": "India's defence indigenization push (Make in India), new orders from Defence PSUs, capacity expansion, BESS subsidiary, FY27 guidance 25-30% revenue growth",
        "headwinds": "Micro-cap with limited liquidity, BSE-only listing, concentrated client base (defence PSUs), small revenue base (Rs 77 Cr)",
        "governance": "Listed Jan 2026 on BSE. New defence subsidiary formed. Rs 51.74 Cr capacity expansion announced. Clean balance sheet (D/E 0.04).",
        "analyst_consensus": "No formal analyst coverage (micro-cap). PE at deep discount to defence sector peers.",
        "analyst_pct": "No formal coverage available (micro-cap stock)",
        "target_prices": "No formal analyst targets. Market cap Rs 342 Cr.",
        "risks": "Micro-cap liquidity risk, concentrated defence client base, order lumpy-ness, BSE-only listing limits institutional interest, small scale",
        "volatility": "High. 52-week range Rs 72.95 to Rs 133.90. Micro-cap with wide price swings. ~83% spread from low to high.",
        "plain_english": "Digilogic makes specialized testing and radar simulation equipment for India's military and aerospace sector. It's a tiny company (Rs 342 crore market cap) but growing fast — profits jumped 34% and it has almost zero debt. India's push to build its own defence equipment ('Make in India') is a big tailwind. The company just announced Rs 52 crore in expansion plans and got a fresh defence order. The risk is that it's very small, trades only on one exchange, and depends heavily on government defence contracts, which can be lumpy."
    },
]

# ─── GOVERNMENT TRACKER DATA ───
govt_tracker = [
    {
        "company": "Coal India (COALINDIA)",
        "action": "Government sold 2% stake via OFS, raising ~Rs 5,500 Cr",
        "date": "2026 (H1)",
        "plain_english": "The government sold a small slice of its ownership in Coal India to raise money. This is part of a bigger plan to raise Rs 80,000 Cr by selling stakes in state-owned companies this year."
    },
    {
        "company": "NHPC Ltd (NHPC)",
        "action": "Government sold 6% stake via OFS, raising Rs 4,357 Cr",
        "date": "2026 (H1)",
        "plain_english": "NHPC runs hydropower plants. The government sold 6% of its shares to public investors to raise funds. This dilutes government ownership slightly but brings in cash for the budget."
    },
    {
        "company": "GIC Re (GICRE)",
        "action": "Government sold 5% stake via OFS, raising Rs 3,090 Cr",
        "date": "2026 (H1)",
        "plain_english": "General Insurance Corporation is India's main reinsurance company. Government sold a 5% stake. Such sales can increase the stock's availability in the market (called 'free float'), which is generally seen as healthy."
    },
    {
        "company": "IDBI Bank (IDBI)",
        "action": "Strategic sale process underway — Expression of Interest received",
        "date": "Ongoing 2026",
        "plain_english": "The government and LIC together own most of IDBI Bank and want to sell their combined ~60% stake to a private buyer. This is one of India's biggest-ever bank privatization attempts. The process is moving forward."
    },
    {
        "company": "BEML, SCI, NMDC Steel, HLL Lifecare, PDIL",
        "action": "Strategic disinvestment Expression of Interest completed for all five",
        "date": "2026",
        "plain_english": "The government wants to sell off five more state-run companies to private buyers. Potential buyers have submitted their interest. These are in sectors like mining equipment (BEML), shipping (SCI), and steel (NMDC Steel)."
    },
    {
        "company": "PLI Scheme Beneficiaries (Multiple Sectors)",
        "action": "Rs 2.40 lakh Cr total investment attracted; Rs 21,534 Cr disbursed; 14.15 lakh jobs created across 14 sectors",
        "date": "As of March 2026",
        "plain_english": "The government's scheme to boost domestic manufacturing has attracted massive private investment. Solar panel makers got the most (Rs 64,873 Cr), followed by pharma (Rs 45,158 Cr) and auto (Rs 44,326 Cr). This benefits listed companies in these sectors."
    },
    {
        "company": "FY27 Disinvestment Target",
        "action": "Union Budget 2026-27 set Rs 80,000 Cr target via disinvestment and asset monetization",
        "date": "Feb 2026 Budget",
        "plain_english": "In the February 2026 budget, the finance minister set a target to raise Rs 80,000 crore by selling government stakes in public companies and monetizing assets. So far, about Rs 25,000 Cr has been raised."
    },
]

# ─── PRE-MARKET SIGNALS ───
premarket = """GIFT Nifty trading at 24,402, up 0.41% from previous close of 24,303 — signals mildly positive open. Sensex closed at 77,655 on July 29 (+1.16%, +889 pts). European markets mixed. Fresh FII buying of Rs 755 Cr and DII support of Rs 1,664 Cr provide cushion. India VIX low — subdued volatility expected."""

# ─── CHART GENERATION ───
CHART_DIR = "/sessions/pensive-jolly-hamilton/mnt/outputs"

def create_sentiment_chart():
    """Create horizontal bar chart of sentiment verdicts"""
    fig, ax = plt.subplots(figsize=(7, 3.5))
    names = [s["ticker"] for s in stocks]
    verdicts = [s["verdict"] for s in stocks]
    colors_map = {"Positive": "#27AE60", "Neutral": "#F39C12", "Negative": "#E74C3C"}
    vals = [1 if v == "Positive" else 0.5 if v == "Neutral" else 0 for v in verdicts]
    bar_colors = [colors_map.get(v, "#999") for v in verdicts]

    bars = ax.barh(names, vals, color=bar_colors, height=0.6, edgecolor='white', linewidth=0.5)
    ax.set_xlim(0, 1.2)
    ax.set_xticks([0, 0.5, 1.0])
    ax.set_xticklabels(["Negative", "Neutral", "Positive"], fontsize=8)
    ax.invert_yaxis()
    ax.set_title("Sentiment Overview", fontsize=11, fontweight='bold', color='#1B2A4A', pad=10)
    ax.tick_params(axis='y', labelsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#D5D8DC')
    ax.spines['left'].set_color('#D5D8DC')
    plt.tight_layout()
    path = os.path.join(CHART_DIR, "sentiment_chart.png")
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    return path

def create_price_performance_chart():
    """1-year price performance bar chart"""
    fig, ax = plt.subplots(figsize=(7, 3.5))
    names = [s["ticker"] for s in stocks]
    changes = [s["one_year_change"] for s in stocks]
    bar_colors = ["#27AE60" if c > 0 else "#E74C3C" for c in changes]

    bars = ax.bar(names, changes, color=bar_colors, width=0.6, edgecolor='white', linewidth=0.5)
    ax.axhline(y=0, color='#7F8C8D', linewidth=0.8, linestyle='-')
    ax.set_ylabel("1-Year % Change", fontsize=9)
    ax.set_title("1-Year Price Performance", fontsize=11, fontweight='bold', color='#1B2A4A', pad=10)
    ax.tick_params(axis='x', labelsize=7, rotation=45)
    ax.tick_params(axis='y', labelsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    for bar, val in zip(bars, changes):
        ypos = bar.get_height() + (2 if val >= 0 else -5)
        ax.text(bar.get_x() + bar.get_width()/2, ypos, f"{val:+.0f}%",
                ha='center', va='bottom' if val >= 0 else 'top', fontsize=7, fontweight='bold')

    plt.tight_layout()
    path = os.path.join(CHART_DIR, "performance_chart.png")
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    return path

def create_pe_chart():
    """P/E valuation snapshot bar chart"""
    fig, ax = plt.subplots(figsize=(7, 3.5))
    names = [s["ticker"] for s in stocks]
    pes = [s["pe"] for s in stocks]
    # Cap display at 60 for readability
    pes_display = [min(p, 60) if p > 0 else 0 for p in pes]
    bar_colors = []
    for p in pes:
        if p < 0 or p == 0:
            bar_colors.append("#95A5A6")
        elif p < 20:
            bar_colors.append("#27AE60")
        elif p < 40:
            bar_colors.append("#F39C12")
        else:
            bar_colors.append("#E74C3C")

    bars = ax.bar(names, pes_display, color=bar_colors, width=0.6, edgecolor='white', linewidth=0.5)
    ax.axhline(y=20, color='#27AE60', linewidth=0.8, linestyle='--', alpha=0.5, label='Value zone')
    ax.axhline(y=40, color='#E74C3C', linewidth=0.8, linestyle='--', alpha=0.5, label='Expensive zone')
    ax.set_ylabel("P/E Ratio", fontsize=9)
    ax.set_title("P/E Valuation Snapshot", fontsize=11, fontweight='bold', color='#1B2A4A', pad=10)
    ax.tick_params(axis='x', labelsize=7, rotation=45)
    ax.tick_params(axis='y', labelsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(fontsize=7, loc='upper right')

    for bar, val in zip(bars, pes):
        label = f"{val:.1f}" if val > 0 else "N/A"
        if val > 60:
            label = f"{val:.0f}"
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, label,
                ha='center', va='bottom', fontsize=6.5, fontweight='bold')

    plt.tight_layout()
    path = os.path.join(CHART_DIR, "pe_chart.png")
    plt.savefig(path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    return path

# ─── PDF BUILDER ───
def build_pdf():
    report_date = "2026-07-30"
    filename = f"Daily_Stock_Watchlist_Report_{report_date}.pdf"
    filepath = os.path.join(CHART_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=50,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle(
        name='CoverTitle',
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=NAVY,
        alignment=TA_CENTER,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name='CoverSubtitle',
        fontName='Helvetica',
        fontSize=11,
        textColor=TEXT_LIGHT,
        alignment=TA_CENTER,
        spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        name='SectionTitle',
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=NAVY,
        spaceBefore=16,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name='StockHeader',
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=WHITE,
        spaceBefore=0,
        spaceAfter=0,
    ))
    styles.add(ParagraphStyle(
        name='BodyText2',
        fontName='Helvetica',
        fontSize=9,
        textColor=TEXT_DARK,
        alignment=TA_JUSTIFY,
        leading=13,
        spaceBefore=2,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name='SmallBold',
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=TEXT_DARK,
        leading=12,
    ))
    styles.add(ParagraphStyle(
        name='SmallText',
        fontName='Helvetica',
        fontSize=8.5,
        textColor=TEXT_DARK,
        leading=12,
        alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        name='PlainEnglish',
        fontName='Helvetica',
        fontSize=9,
        textColor=HexColor('#1A5276'),
        leading=13,
        alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        name='TableCell',
        fontName='Helvetica',
        fontSize=8,
        textColor=TEXT_DARK,
        leading=11,
    ))
    styles.add(ParagraphStyle(
        name='TableCellBold',
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=NAVY,
        leading=11,
    ))
    styles.add(ParagraphStyle(
        name='PreMarket',
        fontName='Helvetica',
        fontSize=9,
        textColor=TEXT_DARK,
        leading=13,
        alignment=TA_JUSTIFY,
        spaceBefore=4,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name='Disclaimer',
        fontName='Helvetica',
        fontSize=7,
        textColor=TEXT_LIGHT,
        leading=9,
        alignment=TA_CENTER,
    ))

    story = []

    # ═══ COVER SECTION ═══
    story.append(Spacer(1, 30))

    # Title block
    cover_title_data = [
        [Paragraph("DAILY STOCK WATCHLIST REPORT", styles['CoverTitle'])],
        [Paragraph(f"Generated: {report_date} | Pre-Market Edition (before 9:15 AM IST)", styles['CoverSubtitle'])],
    ]
    cover_table = Table(cover_title_data, colWidths=[doc.width])
    cover_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOX', (0, 0), (-1, -1), 1, NAVY),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 15),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 15))

    # Pre-market signals
    premarket_data = [
        [Paragraph("<b>PRE-MARKET SIGNALS (July 30, 2026)</b>", styles['SmallBold'])],
        [Paragraph(premarket, styles['PreMarket'])],
    ]
    premarket_table = Table(premarket_data, colWidths=[doc.width])
    premarket_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), SECTION_BG),
        ('BACKGROUND', (0, 1), (0, 1), WHITE),
        ('BOX', (0, 0), (-1, -1), 0.5, BLUE_ACCENT),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(premarket_table)
    story.append(Spacer(1, 15))

    # Quick-scan summary table
    story.append(Paragraph("<b>QUICK-SCAN SUMMARY</b>", styles['SectionTitle']))

    summary_header = [
        Paragraph("<b>Stock</b>", styles['TableCellBold']),
        Paragraph("<b>Ticker</b>", styles['TableCellBold']),
        Paragraph("<b>Price</b>", styles['TableCellBold']),
        Paragraph("<b>Verdict</b>", styles['TableCellBold']),
        Paragraph("<b>1Y Change</b>", styles['TableCellBold']),
        Paragraph("<b>P/E</b>", styles['TableCellBold']),
    ]
    summary_rows = [summary_header]

    for s in stocks:
        verdict_color = "#27AE60" if s["verdict"] == "Positive" else "#F39C12" if s["verdict"] == "Neutral" else "#E74C3C"
        change_color = "#27AE60" if s["one_year_change"] > 0 else "#E74C3C"
        pe_str = f"{s['pe']:.1f}" if s['pe'] > 0 else "N/A"
        row = [
            Paragraph(s["name"][:25], styles['TableCell']),
            Paragraph(s["ticker"], styles['TableCell']),
            Paragraph(f"Rs {s['price']:,.1f}", styles['TableCell']),
            Paragraph(f'<font color="{verdict_color}"><b>{s["verdict"]}</b></font>', styles['TableCell']),
            Paragraph(f'<font color="{change_color}"><b>{s["one_year_change"]:+.1f}%</b></font>', styles['TableCell']),
            Paragraph(pe_str, styles['TableCell']),
        ]
        summary_rows.append(row)

    col_widths = [doc.width * 0.28, doc.width * 0.14, doc.width * 0.13, doc.width * 0.13, doc.width * 0.15, doc.width * 0.10]
    summary_table = Table(summary_rows, colWidths=col_widths)
    summary_style = [
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]

    # Color-code verdict cells
    for i, s in enumerate(stocks, 1):
        if s["verdict"] == "Positive":
            summary_style.append(('BACKGROUND', (3, i), (3, i), HexColor('#E8F8F5')))
        elif s["verdict"] == "Neutral":
            summary_style.append(('BACKGROUND', (3, i), (3, i), HexColor('#FEF9E7')))
        else:
            summary_style.append(('BACKGROUND', (3, i), (3, i), HexColor('#FDEDEC')))

    summary_table.setStyle(TableStyle(summary_style))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # ═══ CHARTS ═══
    sentiment_path = create_sentiment_chart()
    perf_path = create_price_performance_chart()
    pe_path = create_pe_chart()

    # Map to file-tool paths for reportlab
    sentiment_local = os.path.join(CHART_DIR, "sentiment_chart.png")
    perf_local = os.path.join(CHART_DIR, "performance_chart.png")
    pe_local = os.path.join(CHART_DIR, "pe_chart.png")

    story.append(Spacer(1, 5))
    story.append(Image(sentiment_local, width=doc.width * 0.85, height=180))
    story.append(Spacer(1, 8))
    story.append(Image(perf_local, width=doc.width * 0.85, height=180))
    story.append(Spacer(1, 8))
    story.append(Image(pe_local, width=doc.width * 0.85, height=180))

    # ═══ PART 1 — PER-STOCK SECTIONS ═══
    story.append(PageBreak())
    story.append(Paragraph("PART 1 — DETAILED STOCK ANALYSIS", styles['SectionTitle']))
    story.append(Spacer(1, 8))

    for idx, s in enumerate(stocks):
        stock_elements = []

        # Header bar with company name + ticker + ISIN
        header_data = [[
            Paragraph(f'<font color="white"><b>{s["name"]}</b></font>', styles['StockHeader']),
            Paragraph(f'<font color="white">{s["ticker"]} | {s["isin"]}</font>',
                      ParagraphStyle('HeaderRight', fontName='Helvetica', fontSize=9, textColor=WHITE, alignment=TA_RIGHT)),
        ]]
        header_table = Table(header_data, colWidths=[doc.width * 0.55, doc.width * 0.45])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), NAVY),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        stock_elements.append(header_table)

        # Verdict tag
        verdict_bg = HexColor('#E8F8F5') if s["verdict"] == "Positive" else HexColor('#FEF9E7') if s["verdict"] == "Neutral" else HexColor('#FDEDEC')
        verdict_border = s["verdict_color"]
        verdict_data = [[
            Paragraph(f'<font color="{s["verdict_color"].hexval()}"><b>VERDICT: {s["verdict"].upper()}</b></font> — {s["verdict_reason"]}', styles['SmallText']),
        ]]
        verdict_table = Table(verdict_data, colWidths=[doc.width])
        verdict_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), verdict_bg),
            ('BOX', (0, 0), (-1, -1), 1, verdict_border),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        stock_elements.append(verdict_table)
        stock_elements.append(Spacer(1, 4))

        # Detail table
        detail_rows = []

        # Financials
        fin_text = " | ".join([f"{k}: {v}" for k, v in s["financials"]])
        detail_rows.append([Paragraph("<b>A. Financials</b>", styles['TableCellBold']),
                           Paragraph(fin_text, styles['TableCell'])])
        detail_rows.append([Paragraph("<b>ROE & D/E</b>", styles['TableCellBold']),
                           Paragraph(s["roe_de"], styles['TableCell'])])
        detail_rows.append([Paragraph("<b>P/E & P/B</b>", styles['TableCellBold']),
                           Paragraph(s["pe_hist"], styles['TableCell'])])

        # Sentiment
        detail_rows.append([Paragraph("<b>B. Sentiment</b>", styles['TableCellBold']),
                           Paragraph(s["sentiment"], styles['TableCell'])])
        detail_rows.append([Paragraph("<b>Tailwinds</b>", styles['TableCellBold']),
                           Paragraph(s["tailwinds"], styles['TableCell'])])
        detail_rows.append([Paragraph("<b>Headwinds</b>", styles['TableCellBold']),
                           Paragraph(s["headwinds"], styles['TableCell'])])
        detail_rows.append([Paragraph("<b>Governance</b>", styles['TableCellBold']),
                           Paragraph(s["governance"], styles['TableCell'])])

        # Analyst Consensus
        detail_rows.append([Paragraph("<b>C. Analyst View</b>", styles['TableCellBold']),
                           Paragraph(s["analyst_consensus"], styles['TableCell'])])
        detail_rows.append([Paragraph("<b>Buy/Hold/Sell</b>", styles['TableCellBold']),
                           Paragraph(s["analyst_pct"], styles['TableCell'])])
        detail_rows.append([Paragraph("<b>Target Prices</b>", styles['TableCellBold']),
                           Paragraph(s["target_prices"], styles['TableCell'])])

        # Risk
        detail_rows.append([Paragraph("<b>D. Risks</b>", styles['TableCellBold']),
                           Paragraph(s["risks"], styles['TableCell'])])
        detail_rows.append([Paragraph("<b>Volatility</b>", styles['TableCellBold']),
                           Paragraph(s["volatility"], styles['TableCell'])])

        detail_table = Table(detail_rows, colWidths=[doc.width * 0.18, doc.width * 0.82])
        detail_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.3, BORDER_COLOR),
            ('BACKGROUND', (0, 0), (0, -1), LIGHT_GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        stock_elements.append(detail_table)
        stock_elements.append(Spacer(1, 4))

        # Plain English box
        pe_data = [[
            Paragraph('<b>IN PLAIN ENGLISH</b>', ParagraphStyle('PEHeader', fontName='Helvetica-Bold', fontSize=9, textColor=HexColor('#1A5276'))),
        ], [
            Paragraph(s["plain_english"], styles['PlainEnglish']),
        ]]
        pe_table = Table(pe_data, colWidths=[doc.width])
        pe_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#EBF5FB')),
            ('BOX', (0, 0), (-1, -1), 1, BLUE_ACCENT),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        stock_elements.append(pe_table)
        stock_elements.append(Spacer(1, 14))

        # Use KeepTogether so each stock block stays on one page if possible
        story.append(KeepTogether(stock_elements))

    # ═══ PART 2 — GOVERNMENT INVESTMENT TRACKER ═══
    story.append(PageBreak())
    story.append(Paragraph("PART 2 — GOVERNMENT INVESTMENT TRACKER", styles['SectionTitle']))
    story.append(Paragraph("Recent government investments, disinvestments, and policy moves affecting listed companies (last 1-2 weeks / recent activity)", styles['BodyText2']))
    story.append(Spacer(1, 10))

    govt_header = [
        Paragraph("<b>Company / Scheme</b>", styles['TableCellBold']),
        Paragraph("<b>Government Action</b>", styles['TableCellBold']),
        Paragraph("<b>Date / Period</b>", styles['TableCellBold']),
        Paragraph("<b>In Plain English</b>", styles['TableCellBold']),
    ]
    govt_rows = [govt_header]
    for g in govt_tracker:
        govt_rows.append([
            Paragraph(g["company"], styles['TableCell']),
            Paragraph(g["action"], styles['TableCell']),
            Paragraph(g["date"], styles['TableCell']),
            Paragraph(g["plain_english"], styles['TableCell']),
        ])

    govt_col_widths = [doc.width * 0.18, doc.width * 0.28, doc.width * 0.12, doc.width * 0.42]
    govt_table = Table(govt_rows, colWidths=govt_col_widths)
    govt_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(govt_table)
    story.append(Spacer(1, 20))

    # Disclaimer
    disclaimer_text = """DISCLAIMER: This report is for informational purposes only. It provides descriptive analysis, market commentary, and sentiment tracking based on publicly available data.
It does NOT constitute financial advice, a recommendation, or a solicitation to buy, sell, or hold any security. Past performance is not indicative of future results.
All data sourced from public financial databases, brokerage reports, and news as of July 30, 2026. Always consult a SEBI-registered advisor before making investment decisions."""
    story.append(Paragraph(disclaimer_text, styles['Disclaimer']))

    # Build
    doc.build(story)
    print(f"PDF generated: {filepath}")
    return filepath

if __name__ == "__main__":
    build_pdf()
