"""
Send the daily stock watchlist email via SendGrid (primary) or generic SMTP (fallback).
Input:  data/email_body.html
Env:    SENDGRID_API_KEY, MAIL_TO (comma-separated for multiple recipients), EMAIL_FROM (optional),
        SMTP_HOST, SMTP_PORT (465=SSL, 587=STARTTLS), SMTP_USER, SMTP_PASS
"""
import json
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from config import (
    DATA_DIR, EMAIL_FROM, MAIL_TO, SENDGRID_API_KEY,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS,
)

IST = timezone(timedelta(hours=5, minutes=30))


def get_subject(ta_data: dict) -> str:
    """Build email subject line with report date."""
    date_str = ta_data.get("date", datetime.now(IST).strftime("%Y-%m-%d"))
    try:
        date_formatted = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %b %Y")
    except Exception:
        date_formatted = date_str
    return f"Repati Kosam {date_formatted}"


def send_via_sendgrid(to: list[str], subject: str, html_body: str, from_email: str):
    """Send email using SendGrid v3 API."""
    payload = json.dumps({
        "personalizations": [{"to": [{"email": addr} for addr in to]}],
        "from": {"email": from_email.split("<")[-1].rstrip(">").strip() if "<" in from_email else from_email,
                 "name": from_email.split("<")[0].strip() if "<" in from_email else "Stock Watchlist"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_body}],
    }).encode()

    req = Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=payload,
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=30) as resp:
            status = resp.status
        if status in (200, 201, 202):
            print(f"✅ Email sent via SendGrid to {', '.join(to)}")
            return True
        else:
            print(f"⚠ SendGrid returned status {status}")
            return False
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"❌ SendGrid error {e.code}: {body[:200]}")
        return False


def send_via_smtp(to: list[str], subject: str, html_body: str, from_email: str):
    """Fallback: send via generic SMTP. Requires SMTP_HOST, SMTP_USER, SMTP_PASS env vars."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        print("❌ SMTP fallback unavailable: SMTP_HOST, SMTP_USER and SMTP_PASS not all set.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to)

    # Plain text fallback
    text_body = f"Daily Stock Watchlist Report — view in browser or enable HTML email."
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
        with server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to, msg.as_string())
        print(f"✅ Email sent via SMTP ({SMTP_HOST}) to {', '.join(to)}")
        return True
    except Exception as e:
        print(f"❌ SMTP error: {e}")
        return False


def main():
    # Load email body
    email_path = DATA_DIR / "email_body.html"
    if not email_path.exists():
        print("❌ data/email_body.html not found. Run generate_email.py first.")
        sys.exit(1)

    with open(email_path) as f:
        html_body = f.read()

    # Load TA data for subject line
    ta_path = DATA_DIR / "ta_results.json"
    ta_data = {}
    if ta_path.exists():
        with open(ta_path) as f:
            ta_data = json.load(f)

    subject = get_subject(ta_data)
    to = [addr.strip() for addr in MAIL_TO.split(",") if addr.strip()]
    from_email = EMAIL_FROM

    if not to:
        print("❌ MAIL_TO not configured. Set it in env or config.py.")
        sys.exit(1)

    print(f"📧 Sending: {subject}")
    print(f"   To: {', '.join(to)}")

    # Try SendGrid first
    if SENDGRID_API_KEY:
        if send_via_sendgrid(to, subject, html_body, from_email):
            return
        print("⚠ SendGrid failed, trying SMTP fallback...")

    # Fallback to SMTP
    if send_via_smtp(to, subject, html_body, from_email):
        return

    print("❌ All email methods failed. Report is still available on GitHub Pages.")
    # Don't exit with error — the data is deployed to GitHub Pages either way


if __name__ == "__main__":
    main()
