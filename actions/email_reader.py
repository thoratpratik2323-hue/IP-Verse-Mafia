import logging
import imaplib
import email
from email.header import decode_header
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

def email_reader(parameters: dict, player=None) -> str:
    action = parameters.get("action", "fetch_unread").lower().strip()
    
    creds = get_email_credentials()
    email_user = parameters.get("email") or creds.get("email")
    email_pass = parameters.get("password") or creds.get("password")
    imap_server = parameters.get("imap_server") or creds.get("imap_server") or "imap.gmail.com"
    
    if not email_user or not email_pass:
        return "I need email credentials to check your inbox. Please configure 'email_credentials' in config/api_keys.json, sir."
        
    if action == "fetch_unread":
        try:
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(email_user, email_pass)
            mail.select("inbox")
            
            status, response = mail.search(None, 'UNSEEN')
            if status != "OK":
                return "Failed to search mail inbox, sir."
                
            mail_ids = response[0].split()
            if not mail_ids:
                mail.logout()
                return "You have no unread emails in your inbox, sir!"
                
            output = ["### [INBOX] Recent Unread Emails:\n"]
            latest_ids = mail_ids[-3:]
            latest_ids.reverse()
            
            for idx, mail_id in enumerate(latest_ids, 1):
                res, msg_data = mail.fetch(mail_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8", errors="ignore")
                            
                        from_sender, encoding = decode_header(msg["From"])[0]
                        if isinstance(from_sender, bytes):
                            from_sender = from_sender.decode(encoding or "utf-8", errors="ignore")
                            
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disp = str(part.get("Content-Disposition"))
                                if content_type == "text/plain" and "attachment" not in content_disp:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        body = payload.decode(errors="ignore")
                                        break
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body = payload.decode(errors="ignore")
                                
                        snippet = body.strip()[:120].replace("\n", " ")
                        if len(body) > 120:
                            snippet += "..."
                        output.append(f"{idx}. **From**: {from_sender}\n   *Subject*: {subject}\n   *Snippet*: {snippet}\n")
                        
            mail.logout()
            return "\n".join(output)
            
        except Exception as e:
            return f"Failed to connect or fetch emails: {e}, sir."
            
    else:
        return "Unknown email reader action, sir."
