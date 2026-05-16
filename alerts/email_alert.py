# ─── alerts/email_alert.py ───────────────────────────────────────
# Sends a Gmail alert when the suspicion score threshold is crossed.
#
# Credentials are loaded from .env — never hardcoded.
# The email tells the user what triggered the alert, the timestamp,
# and instructs them to reply with RESET to clear the score.
#
# Note: The reset reply is informational for now — the actual reset
# is handled by pressing R in the main window. A full email-reply
# listener can be added as a future improvement.

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS    = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL  = os.getenv("RECIPIENT_EMAIL")


def send_alert_email(triggers: list, score: float):
    """
    Send an alert email.

    Parameters
    ----------
    triggers : list of strings describing what fired
               e.g. ["Person in restricted zone", "Lockpicking detected"]
    score    : the suspicion score that crossed the threshold
    """
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD or not RECIPIENT_EMAIL:
        print("[EMAIL] Missing credentials in .env — email not sent.")
        return

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ── Build email body ──────────────────────────────────────
        trigger_lines = "\n".join(f"  - {t}" for t in triggers)
        body = f"""
SECURITY ALERT — SmartCCTV System
==================================
Time      : {timestamp}
Score     : {score:.0f} / 100

Triggers detected:
{trigger_lines}

The system has flagged suspicious activity. Please review your camera feed immediately.

To reset the suspicion score, press R on the monitoring window,
or reply to this email with the word RESET.

--
SmartCCTV Automated Alert System
        """.strip()

        # ── Build message ─────────────────────────────────────────
        msg = MIMEMultipart()
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = RECIPIENT_EMAIL
        msg["Subject"] = f"[ALERT] Suspicious Activity Detected — {timestamp}"
        msg.attach(MIMEText(body, "plain"))

        # ── Send via Gmail SMTP ───────────────────────────────────
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())

        print(f"[EMAIL] Alert sent to {RECIPIENT_EMAIL}")

    except Exception as e:
        print(f"[EMAIL] Failed to send: {e}")