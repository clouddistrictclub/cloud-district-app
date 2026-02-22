"""
Email utility for Cloud District Club.
Scaffolded for Google Workspace SMTP integration.
NOT activated yet — requires SMTP_USER and SMTP_PASS to be configured in .env.
"""
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'admin@clouddistrict.club')

BUSINESS_PHONE = '608-301-7091'


def is_email_configured() -> bool:
    return bool(SMTP_USER and SMTP_PASS)


def send_email(to: str, subject: str, html_body: str) -> bool:
    """Send an email via SMTP. Returns True on success, False if not configured or on error."""
    if not is_email_configured():
        logging.warning("Email not sent — SMTP credentials not configured.")
        return False

    msg = MIMEMultipart('alternative')
    msg['From'] = FROM_EMAIL
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(FROM_EMAIL, to, msg.as_string())
        logging.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as e:
        logging.error(f"Email send failed to {to}: {e}")
        return False


def build_order_confirmation_html(order_id: str, items: list, total: float) -> str:
    """Build order confirmation email HTML body."""
    rows = ''.join(
        f'<tr><td style="padding:8px;border-bottom:1px solid #333">{item["name"]}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #333;text-align:center">{item["quantity"]}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #333;text-align:right">${item["price"]:.2f}</td></tr>'
        for item in items
    )
    return f"""
    <div style="background:#0c0c0c;color:#fff;padding:32px;font-family:sans-serif;max-width:600px;margin:auto">
      <h1 style="color:#2E6BFF;margin:0 0 8px">Cloud District Club</h1>
      <p style="color:#999;margin:0 0 24px">Order Confirmation</p>
      <p>Your order <strong>#{order_id[:8].upper()}</strong> has been received and is being prepared for pickup.</p>
      <table style="width:100%;border-collapse:collapse;margin:16px 0">
        <thead><tr style="color:#999">
          <th style="text-align:left;padding:8px;border-bottom:2px solid #333">Item</th>
          <th style="text-align:center;padding:8px;border-bottom:2px solid #333">Qty</th>
          <th style="text-align:right;padding:8px;border-bottom:2px solid #333">Price</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="text-align:right;font-size:18px;font-weight:bold;color:#2E6BFF">Total: ${total:.2f}</p>
      <hr style="border-color:#333;margin:24px 0"/>
      <p style="color:#999;font-size:13px">Questions? Call us at {BUSINESS_PHONE} or reply to this email.</p>
    </div>
    """
