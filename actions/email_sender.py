import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
API_KEYS_PATH = CONFIG_DIR / "api_keys.json"

def get_email_credentials() -> dict:
    if API_KEYS_PATH.exists():
        try:
            data = json.loads(API_KEYS_PATH.read_text(encoding="utf-8"))
            return data.get("email_credentials", {})
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)
    return {}

def send_email(parameters: dict, player=None, speak=None) -> str:
    """
    Compose and send emails via Gmail SMTP.
    Parameters:
      to_email (str): Recipient email address
      subject (str): Email subject
      body (str): Email message content
    """
    to_email = parameters.get("to_email")
    subject = parameters.get("subject", "No Subject")
    body = parameters.get("body", "")
    
    creds = get_email_credentials()
    email_user = parameters.get("email") or creds.get("email")
    email_pass = parameters.get("password") or creds.get("password")
    smtp_server = parameters.get("smtp_server") or creds.get("smtp_server") or "smtp.gmail.com"
    smtp_port = int(parameters.get("smtp_port") or creds.get("smtp_port") or 587)
    
    if not email_user or not email_pass:
        msg = "I need email credentials to send emails, sir. Please configure 'email_credentials' in config/api_keys.json."
        if speak:
            speak(msg)
        return msg
        
    if not to_email:
        msg = "Please specify the recipient email ('to_email'), sir."
        if speak:
            speak(msg)
        return msg
        
    try:
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_user, email_pass)
        text = msg.as_string()
        server.sendmail(email_user, to_email, text)
        server.quit()
        
        result_msg = f"Email sent successfully to {to_email}, sir!"
        if speak:
            speak(f"सर, मैंने {to_email} को ईमेल भेज दिया है।")
        if player:
            player.write_log(f"SATURDAY: {result_msg}")
        return result_msg
    except Exception as e:
        err_msg = f"Failed to send email to {to_email}: {e}, sir."
        if speak:
            speak("सर, ईमेल भेजने में कुछ दिक्कत आ रही है।")
        if player:
            player.write_log(f"SYS ERR: {err_msg}")
        return err_msg
