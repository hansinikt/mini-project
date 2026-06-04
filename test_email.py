# test_email.py — run this directly to test email sending
# python test_email.py

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

GMAIL_ADDRESS      = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
RECIPIENT_EMAIL    = os.getenv("RECIPIENT_EMAIL")

print(f"Sending from : {GMAIL_ADDRESS}")
print(f"Sending to   : {RECIPIENT_EMAIL}")
print(f"Password set : {'Yes' if GMAIL_APP_PASSWORD else 'No'}")

try:
    msg = MIMEMultipart()
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = RECIPIENT_EMAIL
    msg["Subject"] = "SmartCCTV Test Email"
    msg.attach(MIMEText("This is a test email from SmartCCTV.", "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())

    print("Email sent successfully!")

except Exception as e:
    print(f"Failed: {e}")