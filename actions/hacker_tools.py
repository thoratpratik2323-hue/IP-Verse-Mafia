import base64
import hashlib
import os
import re
from pathlib import Path

def hacker_action(parameters: dict, player=None, session_memory=None) -> str:
    """
    Cybersecurity and Hacker Toolkit router.
    Supported actions: 'codec', 'hash_identify', 'password_audit', 'encrypt_file', 'decrypt_file'
    """
    act = parameters.get("action", "hash_identify").lower().strip()
    
    if act == "codec":
        return run_codec(parameters)
    elif act == "password_audit":
        return run_password_audit(parameters)
    elif act == "encrypt_file":
        return run_file_crypt(parameters, encrypt=True)
    elif act == "decrypt_file":
        return run_file_crypt(parameters, encrypt=False)
    else:
        return run_hash_identify(parameters)

def run_codec(parameters: dict) -> str:
    operation = parameters.get("operation", "decode").lower().strip()
    encoding_type = parameters.get("type", "base64").lower().strip()
    text = parameters.get("text", "").strip()

    if not text:
        return "Please supply the target text for codec operation, sir."

    try:
        if operation == "encode":
            if encoding_type == "hex":
                res = text.encode("utf-8").hex()
            else: # base64
                res = base64.b64encode(text.encode("utf-8")).decode("utf-8")
            return f"Encoded result ({encoding_type}): {res}"
        else: # decode
            if encoding_type == "hex":
                res = bytes.fromhex(text).decode("utf-8")
            else: # base64
                res = base64.b64decode(text.encode("utf-8")).decode("utf-8")
            return f"Decoded result ({encoding_type}): {res}"
    except Exception as e:
        return f"Codec operation failed: {e}, sir."

def run_hash_identify(parameters: dict) -> str:
    hash_str = parameters.get("hash", "").strip()
    if not hash_str:
        return "Please supply a hash string to identify, sir."

    length = len(hash_str)
    # Check if character format is hexadecimal
    is_hex = bool(re.match(r"^[0-9a-fA-F]+$", hash_str))
    
    if not is_hex:
        return "The string does not appear to be a valid hexadecimal hash, sir."

    if length == 32:
        guess = "MD5"
    elif length == 40:
        guess = "SHA-1"
    elif length == 56:
        guess = "SHA-224"
    elif length == 64:
        guess = "SHA-256"
    elif length == 96:
        guess = "SHA-384"
    elif length == 128:
        guess = "SHA-512"
    else:
        guess = f"Unknown hash format (length: {length})"

    return f"Hash Identification Result: This {length}-character hex string matches the pattern of a **{guess}** hash, sir."

def run_password_audit(parameters: dict) -> str:
    password = parameters.get("password", "").strip()
    if not password:
        return "Please supply a password string to audit, sir."

    length = len(password)
    
    # Calculate entropy
    charset_size = 0
    if re.search(r"[a-z]", password): charset_size += 26
    if re.search(r"[A-Z]", password): charset_size += 26
    if re.search(r"[0-9]", password): charset_size += 10
    if re.search(r"[^a-zA-Z0-9]", password): charset_size += 33
    
    if charset_size == 0:
        return "Invalid password format, sir."
        
    entropy = length * (charset_size ** 0.5)  # Quick estimation formula
    
    strength = "WEAK"
    if length >= 12 and charset_size > 50:
        strength = "VERY STRONG"
    elif length >= 8 and charset_size > 30:
        strength = "MEDIUM / STRONG"

    suggestions = []
    if length < 10:
        suggestions.append("increase length to at least 12 characters")
    if not re.search(r"[A-Z]", password):
        suggestions.append("add uppercase letters")
    if not re.search(r"[0-9]", password):
        suggestions.append("add numbers")
    if not re.search(r"[^a-zA-Z0-9]", password):
        suggestions.append("add special characters")

    suggestion_str = f" Suggestions to improve: {', '.join(suggestions)}." if suggestions else " Excellent password strength!"
    return f"Password Audit: Strength is **{strength}** (length: {length}, entropy index: {entropy:.1f}).{suggestion_str}"

def run_file_crypt(parameters: dict, encrypt: bool = True) -> str:
    file_path_str = parameters.get("file_path", "").strip()
    key = parameters.get("key", "").strip()

    if not file_path_str or not key:
        return "Please provide both the file path and encryption key, sir."

    path = Path(file_path_str)
    if not path.exists():
        return f"File does not exist: {file_path_str}, sir."

    try:
        # Simple, fast key-based XOR cipher for self-contained symmetric encryption
        data = path.read_bytes()
        key_bytes = key.encode("utf-8")
        key_len = len(key_bytes)
        
        result_bytes = bytearray(len(data))
        for idx in range(len(data)):
            result_bytes[idx] = data[idx] ^ key_bytes[idx % key_len]

        # Save back
        suffix = ".enc" if encrypt else ""
        if not encrypt and path.suffix == ".enc":
            out_path = path.with_suffix("")
        else:
            out_path = path.with_name(path.name + suffix)

        out_path.write_bytes(result_bytes)
        action_word = "encrypted" if encrypt else "decrypted"
        return f"File successfully {action_word}! Saved to: '{out_path.name}', sir."
    except Exception as e:
        return f"Encryption/Decryption failed: {e}, sir."
