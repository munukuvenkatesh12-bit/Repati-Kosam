"""
Generate the archive index page from existing archive directories.
Output: site/archive/index.html
"""
import os
from pathlib import Path
from config import SITE_DIR

def main():
    archive_dir = SITE_DIR / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Find all date directories
    dates = sorted(
        [d.name for d in archive_dir.iterdir() if d.is_dir() and d.name[:4].isdigit()],
        reverse=True
    )

    rows = ""
    for date_str in dates:
        date_path = archive_dir / date_str
        has_dashboard = (date_path / "dashboard" / "index.html").exists()
        has_report = (date_path / "report" / "index.html").exists()

        dash_link = f'<a href="{date_str}/dashboard/" style="color:#58a6ff;text-decoration:none;">Dashboard</a>' if has_dashboard else '<span style="color:#484f58;">—</span>'
        report_link = f'<a href="{date_str}/report/" style="color:#58a6ff;text-decoration:none;">Report</a>' if has_report else '<span style="color:#484f58;">—</span>'

        rows += f"""
        <tr style="border-bottom:1px solid #21262d;">
            <td style="padding:10px 16px;font-size:14px;color:#e1e4e8;">{date_str}</td>
            <td style="padding:10px 16px;text-align:center;">{dash_link}</td>
            <td style="padding:10px 16px;text-align:center;">{report_link}</td>
        </tr>"""

    if not rows:
        rows = '<tr><td colspan="3" style="padding:20px;text-align:center;color:#8b949e;">No archived reports yet.</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Archive — Stock Watchlist</title>
<style>
body {{ background:#0a0e17; color:#e1e4e8; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif; margin:0; padding:20px; }}
.container {{ max-width:700px; margin:0 auto; }}
h1 {{ font-size:22px; margin-bottom:8px; }}
p {{ color:#8b949e; font-size:14px; margin-bottom:20px; }}
a.back {{ color:#58a6ff; text-decoration:none; font-size:14px; }}
table {{ width:100%; border-collapse:collapse; background:#161b22; border-radius:8px; overflow:hidden; }}
th {{ padding:10px 16px; text-align:left; color:#8b949e; font-size:12px; font-weight:600; border-bottom:2px solid #30363d; }}
</style>
</head>
<body>
<div class="container">
    <a class="back" href="../">← Back to latest</a>
    <h1>Report Archive</h1>
    <p>{len(dates)} reports available (last 90 days)</p>
    <table>
        <tr>
            <th>Date</th>
            <th style="text-align:center;">Dashboard</th>
            <th style="text-align:center;">Report</th>
        </tr>
        {rows}
    </table>
</div>
</body>
</html>"""

    out_path = archive_dir / "index.html"
    with open(out_path, "w") as f:
        f.write(html)
    print(f"✅ Archive index → {out_path} ({len(dates)} entries)")


if __name__ == "__main__":
    main()
