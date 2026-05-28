"""
actions/password_tools.py — Local Password Security & Generation Toolkit.

Provides password strength checks, secure generation, memorable passphrases,
and educational hashing/hash verification utilities.
"""

from __future__ import annotations

import hashlib
import logging
import math
import secrets
import string
from pathlib import Path
from typing import Any

logger = logging.getLogger("ip_prime.password_tools")

# 100 highly common passwords for instant local checks
COMMON_PASSWORDS = {
    "123456", "password", "123456789", "12345", "12345678", "qwerty", "1234567",
    "password123", "111111", "123123", "admin", "letmein", "uncrackable", "trustnoone",
    "welcome", "shadow", "master", "hunter2", "dragon", "monkey", "superman", "batman",
    "football", "soccer", "baseball", "iloveyou", "mustang", "princess", "charles",
    "joshua", "daniel", "thomas", "nicholas", "matthew", "andrew", "morgan", "samantha"
}

# Standard word list for memorable passphrases
PASSPHRASE_WORDS = [
    "correct", "horse", "battery", "staple", "solar", "ocean", "forest", "mountain",
    "river", "desert", "stream", "cloud", "shadow", "winter", "summer", "autumn",
    "spring", "window", "mirror", "candle", "planet", "galaxy", "rocket", "anchor",
    "bridge", "castle", "tunnel", "market", "harbor", "island", "temple", "safari"
]

def check_password_strength(password: str) -> str:
    """Calculates password entropy, detects character patterns, and scores strength."""
    if not password:
        return "Password is empty."
        
    length = len(password)
    if password.lower() in COMMON_PASSWORDS:
        return "\u274c **CRITICAL:** This password is extremely common and easily brute-forced! Change it immediately."
        
    # Analyze character pool
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in string.punctuation for c in password)
    
    pool_size = 0
    if has_lower: pool_size += 26
    if has_upper: pool_size += 26
    if has_digit: pool_size += 10
    if has_special: pool_size += len(string.punctuation)
    
    if pool_size == 0:
        return "Invalid characters."
        
    # Entropy = length * log2(pool_size)
    entropy = length * math.log2(pool_size)
    
    # Assess score
    if entropy < 30:
        grade = "Very Weak \ud83d\udd05"
        suggestion = "Increase length significantly and mix character types."
    elif entropy < 50:
        grade = "Weak \ud83d\udd06"
        suggestion = "Use a longer passphrase with a combination of special characters."
    elif entropy < 70:
        grade = "Moderate \ud83d\udd07"
        suggestion = "Add more complexity or extend the character count."
    elif entropy < 90:
        grade = "Strong \ud83d\udd08"
        suggestion = "Very secure! Suitable for general accounts."
    else:
        grade = "Excellent / High Entropy \ud83c\udfaf"
        suggestion = "Superb strength. Highly resistant to brute-force attacks."
        
    return (
        f"**Password Strength Assessment:**\n"
        f"- Length: {length} characters\n"
        f"- Unique character pools: Upper ({has_upper}), Lower ({has_lower}), Digits ({has_digit}), Special ({has_special})\n"
        f"- Entropy Score: {entropy:.2f} bits\n"
        f"- Security Grade: **{grade}**\n"
        f"- Recommendation: *{suggestion}*"
    )

def generate_strong_password(length: int = 16, use_upper: bool = True, use_digits: bool = True, use_special: bool = True) -> str:
    """Generates a cryptographically secure random password."""
    chars = string.ascii_lowercase
    if use_upper:
        chars += string.ascii_uppercase
    if use_digits:
        chars += string.digits
    if use_special:
        chars += string.punctuation
        
    if length < 8:
        length = 8
        
    password = "".join(secrets.choice(chars) for _ in range(length))
    return f"Generated Secure Password:\n`{password}`"

def generate_passphrase(words_count: int = 4) -> str:
    """Generates a memorable passphrase using cryptographically selected words."""
    if words_count < 3:
        words_count = 3
    selected = [secrets.choice(PASSPHRASE_WORDS) for _ in range(words_count)]
    passphrase = "-".join(selected)
    return f"Generated Passphrase (Memorable):\n`{passphrase}`"

def hash_password(password: str, algorithm: str = "sha256") -> str:
    """Hashes a text string using standard algorithms for educational purposes."""
    algo = algorithm.strip().lower()
    encoded = password.encode("utf-8")
    
    if algo == "md5":
        res = hashlib.md5(encoded).hexdigest()
    elif algo == "sha1":
        res = hashlib.sha1(encoded).hexdigest()
    elif algo == "sha256":
        res = hashlib.sha256(encoded).hexdigest()
    elif algo == "sha512":
        res = hashlib.sha512(encoded).hexdigest()
    elif algo == "bcrypt":
        try:
            import bcrypt
            # salt length factor is 12
            hashed = bcrypt.hashpw(encoded, bcrypt.gensalt(12))
            res = hashed.decode("utf-8")
        except ImportError:
            return "Bcrypt library not installed. Standard fallback SHA-256 instead."
    else:
        return f"Unsupported algorithm: {algorithm}. Use MD5, SHA1, SHA256, or bcrypt."
        
    return f"Hashed value ({algorithm.upper()}):\n`{res}`"

def crack_hash_wordlist(hash_to_crack: str, algorithm: str, wordlist_path: str, confirmed: str = "no", player: Any = None) -> str:
    """
    Attempts to reverse a local hash value by trying words from a user-supplied text wordlist.
    Only permitted on hashes that the user explicitly confirms they possess authorized scope for.
    """
    if confirmed.strip().lower() != "yes":
        return (
            "\u274c **Consent Required:** Hashing analysis / verification is only permitted "
            "on target datasets that you legally own or are authorized to audit.\n"
            "Please confirm scope by passing parameter: `confirmed='yes'`"
        )
        
    p = Path(wordlist_path).resolve()
    if not p.exists() or not p.is_file():
        return f"Wordlist file not found at: {wordlist_path}"
        
    algo = algorithm.strip().lower()
    target = hash_to_crack.strip().lower()
    
    try:
        words = p.read_text(encoding="utf-8", errors="replace").splitlines()
        for word in words:
            word = word.strip()
            # Calculate match hash
            encoded = word.encode("utf-8")
            if algo == "md5":
                h = hashlib.md5(encoded).hexdigest()
            elif algo == "sha1":
                h = hashlib.sha1(encoded).hexdigest()
            elif algo == "sha256":
                h = hashlib.sha256(encoded).hexdigest()
            elif algo == "sha512":
                h = hashlib.sha512(encoded).hexdigest()
            else:
                return f"Unsupported hash crack algorithm: {algorithm}."
                
            if h == target:
                return f"\ud83c\udf89 **Success!** Hash cracked!\nPlaintext representation: **{word}**"
                
        return f"Failed to crack hash. Checked {len(words)} candidates from the wordlist."
    except Exception as e:
        return f"An error occurred while parsing the wordlist: {e}"

def check_common_passwords(password: str) -> str:
    """Verifies if the password belongs to the standard common passwords directory."""
    if password.strip() in COMMON_PASSWORDS:
        return "\u26a0\ufe0f **WARNING:** This password is extremely common! Avoid utilizing it."
    return "\u2705 The password was not found in the basic list of common passwords."

def password_tools(parameters: dict[str, Any], player: Any = None) -> str:
    """
    Main orchestrator for password utilities.
    """
    action = parameters.get("action", "").lower().strip()
    text = parameters.get("text", "")
    
    if action == "strength":
        return check_password_strength(text)
    elif action == "generate_strong":
        length = int(parameters.get("length", 16))
        upper = parameters.get("use_upper", True)
        digits = parameters.get("use_digits", True)
        special = parameters.get("use_special", True)
        return generate_strong_password(length, upper, digits, special)
    elif action == "generate_passphrase":
        count = int(parameters.get("words_count", 4))
        return generate_passphrase(count)
    elif action == "hash":
        algo = parameters.get("algorithm", "sha256")
        return hash_password(text, algo)
    elif action == "crack":
        algo = parameters.get("algorithm", "sha256")
        wl = parameters.get("wordlist_path", "")
        confirm = parameters.get("confirmed", "no")
        return crack_hash_wordlist(text, algo, wl, confirm, player)
    elif action == "check_common":
        return check_common_passwords(text)
    else:
        return f"Unknown password_tools action '{action}'."
