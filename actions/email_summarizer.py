"""
email_summarizer.py — Parses local folders and Outlook directories to build email action logs.

This is a standard action module for the IP Prime personal assistant suite.
"""

import os
import json
import subprocess
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
API_KEYS_PATH = BASE_DIR / "config" / "api_keys.json"

def _get_gemini_client():
    """Loads API key and returns a Gemini Client from the new google-genai SDK."""
    try:
        from google import genai
        if API_KEYS_PATH.exists():
            with open(API_KEYS_PATH, "r", encoding="utf-8") as f:
                api_key = json.load(f)["gemini_api_key"]
            return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[EmailSummarizer] Error loading key: {e}")
    return None

def _get_outlook_emails_via_powershell(count: int = 10) -> list:
    """Runs a PowerShell script to fetch local Outlook emails using COM MAPI Interop."""
    ps_command = f"""
    try {{
        $ol = New-Object -ComObject Outlook.Application -ErrorAction Stop
        $ns = $ol.GetNameSpace("MAPI")
        $inbox = $ns.GetDefaultFolder(6)
        $items = $inbox.Items | Sort-Object ReceivedTime -Descending | Select-Object -First {count}
        $list = @()
        foreach ($item in $items) {{
            $body = ""
            if ($item.Body) {{
                $body = $item.Body.SubString(0, [Math]::Min($item.Body.Length, 150))
                # Remove tabs and consecutive newlines for clean JSON
                $body = $body -replace "[\\r\\n\\t]+", " "
            }}
            $list += [PSCustomObject]@{{
                subject = $item.Subject
                sender = $item.SenderName
                date = $item.ReceivedTime.ToString("yyyy-MM-dd HH:mm:ss")
                body = $body
            }}
        }}
        $list | ConvertTo-Json -Compress
    }} catch {{
        Write-Output "[]"
    }}
    """
    try:
        # Run PowerShell silently with execution bypass
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            emails = json.loads(result.stdout.strip())
            # Convert single object to list if necessary
            if isinstance(emails, dict):
                return [emails]
            return emails
    except Exception as e:
        print(f"[EmailSummarizer] PowerShell extraction failed: {e}")
    return []

def _get_emails_from_file(file_path: str) -> list:
    """Parses a local .eml or text file if provided."""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
        # Basic parsing of headers
        sender = "Unknown Sender"
        subject = "No Subject"
        date = "Unknown Date"
        body = []
        body_started = False
        
        for line in lines:
            if not body_started:
                if line.lower().startswith("from:"):
                    sender = line[5:].strip()
                elif line.lower().startswith("subject:"):
                    subject = line[8:].strip()
                elif line.lower().startswith("date:"):
                    date = line[5:].strip()
                elif line.strip() == "":
                    body_started = True
            else:
                body.append(line.strip())
                if len(body) >= 10: # limit preview size
                    break
                    
        return [{
            "sender": sender,
            "subject": subject,
            "date": date,
            "body": " ".join(body)[:150]
        }]
    except Exception as e:
        print(f"[EmailSummarizer] File parsing failed: {e}")
    return []

def _summarize_emails_with_ai(emails: list, player=None) -> str:
    """Uses Gemini 2.0 Flash to synthesize email topics and identify action items."""
    client = _get_gemini_client()
    if not client:
        return "Gemini API key is not configured, sir."
        
    if not emails:
        return "No emails found to summarize, sir."
        
    try:
        if player:
            player.write_thought("Analyzing emails and compiling action items list...")
            
        system_instruction = (
            "You are IP PRIME's Intelligence Executive. "
            "You will be provided with a JSON list of recent emails. "
            "Compile a highly polished executive briefing summarizing the emails for Pratik Sir. "
            "Use a professional, warm, loyal Hinglish style. Your response must follow exactly this layout:\n\n"
            "### [EMAIL] EXECUTIVE EMAIL BRIEFING\n\n"
            "#### 1. INBOX OVERVIEW (Sender, Subject & 1-line summary)\n"
            "- List each email with key details.\n\n"
            "#### 2. [ALERT] ACTION REQUIRED (Urgent replies or tasks)\n"
            "- Highlight critical items that need immediate attention from Pratik Sir. If none, write 'Inbox clean! No immediate action needed, sir.'\n\n"
            "Address the user directly as Pratik Sir, and end with a respectful sign-off."
        )
        
        prompt = f"Analyze these emails, sir:\n\n{json.dumps(emails, indent=4)}"
        
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2
            )
        )
        
        return response.text
        
    except Exception as e:
        return f"Error creating AI email summary: {e}, sir."

def get_email_summary(source: str = 'outlook', file_path: str = '', count: int = 5, player=None) -> str:
    """Main function to retrieve and summarize emails from different sources."""
    emails = []
    mode_info = "Live Outlook Inbox"
    
    if source == 'outlook':
        if player:
            player.write_thought("Accessing local Outlook desktop client via COM Interop...")
        emails = _get_outlook_emails_via_powershell(count)
        if not emails:
            # Fallback to demo if Outlook not configured/running
            source = 'demo'
            
    if source == 'file' and file_path:
        mode_info = f"EML File: {Path(file_path).name}"
        emails = _get_emails_from_file(file_path)
        
    if source == 'demo' or not emails:
        mode_info = "Simulation Mode (Mock Data)"
        # High-fidelity mock emails
        emails = [
            {
                "sender": "HDFC Bank Alert",
                "subject": "Credit Card E-Statement Generated",
                "date": "2026-05-27 08:12:00",
                "body": "Your credit card statement ending in 4321 has been generated. Minimum amount due: 4,500 INR. Total due: 45,000 INR."
            },
            {
                "sender": "Github Security",
                "subject": "[GitHub] Security Alert: Vulnerability detected",
                "date": "2026-05-26 18:45:00",
                "body": "Critical vulnerability found in package 'lodash' inside repository 'ip-prime'. Upgrade to version 4.17.21 is recommended."
            },
            {
                "sender": "Pratik Sir's Client",
                "subject": "Urgent: Project Delivery Roadmap Update",
                "date": "2026-05-26 14:30:00",
                "body": "Pratik bhai, please review the latest Figma screens and the API integration roadmap I shared. We need to deploy our first build by Friday."
            }
        ]
        
    # Generate Gemini summary
    briefing = _summarize_emails_with_ai(emails, player)
    
    header = f"### [EMAIL] Email Intelligence Briefing ({mode_info})\n"
    header += f"- **Total processed**: {len(emails)} emails\n\n"
    
    return header + briefing

def email_summarizer(parameters: dict, player=None) -> str:
    """Dispatcher for email summarizer tool."""
    action = parameters.get("action", "summary").lower().strip()
    source = parameters.get("source", "outlook").lower().strip()
    file_path = parameters.get("file_path", "")
    count = int(parameters.get("count", 5))
    
    if action in ["summary", "outlook", "file"]:
        # If file is explicitly requested and path passed, set source to file
        src = "file" if (action == "file" or file_path) else source
        return get_email_summary(source=src, file_path=file_path, count=count, player=player)
    else:
        return f"Unknown action '{action}' for Email Summarizer, sir."
