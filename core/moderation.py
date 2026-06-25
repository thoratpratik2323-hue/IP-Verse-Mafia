import re

# Simple robust safety keywords and regex patterns
BLOCKED_KEYWORDS = [
    # Vulgarity / Inappropriate content
    r"\b(bastard|motherfucker|asshole|bitch|dickhead|porn|pornography|nsfw|sexually explicit)\b",
    # Malicious/exploit attempts
    r"\b(write a virus|create malware|how to hack a bank|how to build a bomb|bypass windows security)\b",
    # Dangerous destructive commands
    r"\b(format c:|rm -rf /|deltree|wipe master boot record)\b"
]

def moderate_prompt(text: str) -> str | None:
    """
    Checks if a prompt violates safety policies.
    Returns the reason string if blocked, or None if safe.
    """
    if not text:
        return None
        
    text_lower = text.lower().strip()
    
    # Check regex keywords
    for pattern in BLOCKED_KEYWORDS:
        if re.search(pattern, text_lower):
            return "Prompt contains unsafe, toxic, or hazardous instructions."
            
    return None

def moderate_response(text: str) -> str | None:
    """
    Checks if Saturday's generated output contains unsafe content.
    Returns the reason string if blocked, or None if safe.
    """
    if not text:
        return None
        
    text_lower = text.lower().strip()
    
    # Check regex keywords
    for pattern in BLOCKED_KEYWORDS:
        if re.search(pattern, text_lower):
            return "Response generated content that violates safety guidelines."
            
    return None
