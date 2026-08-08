import os
import smtplib
import logging
from email.message import EmailMessage

log = logging.getLogger(__name__)

SMTP_SERVER = "smtp-mail.outlook.com"
SMTP_PORT = 587

def send_email(to_address: str, subject: str, body_content: str) -> bool:
    """
    Sends an email using the Outlook SMTP server.
    Expects OUTLOOK_EMAIL and OUTLOOK_API_KEY environment variables to be set.
    """
    sender_email = os.getenv("OUTLOOK_EMAIL")
    sender_password = os.getenv("OUTLOOK_API_KEY")

    if not sender_email or not sender_password:
        log.warning("OUTLOOK_EMAIL or OUTLOOK_API_KEY is not set. Email will not be sent.")
        return False

    msg = EmailMessage()
    msg.set_content(body_content)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_address

    try:
        log.info(f"Connecting to SMTP server {SMTP_SERVER}:{SMTP_PORT}...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            log.info(f"Successfully sent email to {to_address} with subject '{subject}'")
        return True
    except Exception as e:
        log.error(f"Failed to send email to {to_address}: {e}")
        return False
