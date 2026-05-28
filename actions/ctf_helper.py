"""
actions/ctf_helper.py — Capture The Flag (CTF) Educational Helper Module.

Provides local encoding, decoding, hash classification, local string extraction,
and theoretical tips for solving common security and CTF challenges.
"""

from __future__ import annotations

import base64
import binascii
import codecs
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("ip_prime.ctf_helper")

# Morse code dictionary
MORSE_CODE_DICT = {
    '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E', '..-.': 'F',
    '--.': 'G', '....': 'H', '..': 'I', '.---': 'J', '-.-': 'K', '.-..': 'L',
    '--': 'M', '-.': 'N', '---': 'O', '.--.': 'P', '--.-': 'Q', '.-.': 'R',
    '...': 'S', '-': 'T', '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X',
    '-.--': 'Y', '--..': 'Z', '-----': '0', '.----': '1', '..---': '2',
    '...--': '3', '....-': '4', '.....': '5', '-....': '6', '--...': '7',
    '---..': '8', '----.': '9', '.-.-.-': '.', '--..--': ',', '..--..': '?',
    '-..-.': '/', '-....-': '-', '-...-': '=', '---...': ':', '.-..-.': '"',
    '.----.': "'", '-.-.--': '!'
}

def decode_base64(text: str) -> str:
    """Decodes a base64 encoded string."""
    try:
        decoded = base64.b64decode(text.strip().encode("utf-8")).decode("utf-8", errors="replace")
        return f"Decoded Base64:\n{decoded}"
    except Exception as e:
        return f"Error decoding Base64: {e}"

def decode_hex(text: str) -> str:
    """Decodes a hexadecimal string."""
    clean = re.sub(r"[\s:x\\x]", "", text.strip())
    try:
        decoded = binascii.unhexlify(clean).decode("utf-8", errors="replace")
        return f"Decoded Hex:\n{decoded}"
    except Exception as e:
        return f"Error decoding Hex: {e}"

def decode_rot13(text: str) -> str:
    """Decodes ROT13 text."""
    try:
        decoded = codecs.encode(text, "rot_13")
        return f"ROT13 Decoded:\n{decoded}"
    except Exception as e:
        return f"Error decoding ROT13: {e}"

def decode_morse(text: str) -> str:
    """Decodes standard Morse code (letters separated by space, words by slash or multiple spaces)."""
    try:
        words = text.strip().split(" / ") if " / " in text else text.strip().split("   ")
        decoded_words = []
        for word in words:
            decoded_chars = []
            for char in word.split():
                decoded_chars.append(MORSE_CODE_DICT.get(char, "?"))
            decoded_words.append("".join(decoded_chars))
        decoded = " ".join(decoded_words)
        return f"Decoded Morse Code:\n{decoded}"
    except Exception as e:
        return f"Error decoding Morse code: {e}"

def crack_caesar_cipher(text: str) -> str:
    """Brute-forces all 25 possible rotation shifts of a Caesar cipher."""
    results = ["**Caesar Cipher Brute Force Results:**"]
    for shift in range(1, 26):
        shifted = []
        for char in text:
            if char.isalpha():
                base = ord('A') if char.isupper() else ord('a')
                shifted_char = chr((ord(char) - base - shift) % 26 + base)
                shifted.append(shifted_char)
            else:
                shifted.append(char)
        results.append(f"Shift {shift:02d}: {''.join(shifted)}")
    return "\n".join(results)

def detect_encoding(text: str) -> str:
    """Detects likely encoding standard used for a text snippet."""
    clean = text.strip()
    # Check Hex
    if re.fullmatch(r"([0-9a-fA-F]{2})+", re.sub(r"[\s:x\\x]", "", clean)):
        return "Encoding detected: **Hexadecimal (Base16)**"
    # Check Morse
    if re.fullmatch(r"[\.\-\s/]+", clean):
        return "Encoding detected: **Morse Code**"
    # Check Base64
    if len(clean) % 4 == 0 and re.fullmatch(r"[A-Za-z0-9+/=]+", clean):
        try:
            base64.b64decode(clean.encode("utf-8"))
            return "Encoding detected: **Base64**"
        except Exception:
            pass
    return "Encoding detected: **Unknown or Plain Text**"

def hash_identifier(hash_str: str) -> str:
    """Classifies hash signature based on length and characters."""
    h = hash_str.strip().lower()
    length = len(h)
    
    # Non-hex validation (e.g. bcrypt uses special character sets)
    is_hex = bool(re.fullmatch(r"[0-9a-f]+", h))
    
    if length == 32 and is_hex:
        return "Hash format identified: **MD5** (Length: 32, Hex)"
    elif length == 40 and is_hex:
        return "Hash format identified: **SHA-1** (Length: 40, Hex)"
    elif length == 56 and is_hex:
        return "Hash format identified: **SHA-224** (Length: 56, Hex)"
    elif length == 64 and is_hex:
        return "Hash format identified: **SHA-256** or **NTLM** (Length: 64, Hex)"
    elif length == 96 and is_hex:
        return "Hash format identified: **SHA-384** (Length: 96, Hex)"
    elif length == 128 and is_hex:
        return "Hash format identified: **SHA-512** (Length: 128, Hex)"
    elif h.startswith("$2a$") or h.startswith("$2b$") or h.startswith("$2y$"):
        return "Hash format identified: **bcrypt** (Blowfish-based blowfish hash)"
    elif h.startswith("$pbkdf2"):
        return "Hash format identified: **PBKDF2**"
    else:
        return f"Could not determine hash format. Length: {length}."

def extract_strings(file_path: str) -> str:
    """Extracts printable ASCII strings from local files (analogue of Unix `strings` utility)."""
    p = Path(file_path).resolve()
    if not p.exists() or not p.is_file():
        return f"File not found: {file_path}"
    
    try:
        content = p.read_bytes()
        printable_regex = re.compile(rb'[ -~]{4,}')
        strings = printable_regex.findall(content)
        extracted = [s.decode("ascii") for s in strings[:100]]
        
        if not extracted:
            return f"No readable strings found in file: {p.name}"
        
        output = [f"**Extracted Strings from {p.name} (Top 100):**"]
        output.extend(extracted)
        return "\n".join(output)
    except Exception as e:
        return f"Failed to extract strings: {e}"

def steganography_check(image_path: str) -> str:
    """Reads basic EXIF/metadata tags of an image file to check for hidden stego markers."""
    p = Path(image_path).resolve()
    if not p.exists() or not p.is_file():
        return f"Image file not found: {image_path}"
        
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
    except ImportError:
        return "PIL (Pillow) library required for image steganography check."
        
    try:
        img = Image.open(p)
        info = [
            f"**Steganography Metadata Audit:** {p.name}",
            f"- Format: {img.format}",
            f"- Mode: {img.mode}",
            f"- Size: {img.width}x{img.height}"
        ]
        
        # Check EXIF
        exif = img.getexif()
        if exif:
            info.append("\n**EXIF Tags Found:**")
            for tag_id, value in exif.items():
                tag_name = TAGS.get(tag_id, tag_id)
                info.append(f"  * {tag_name}: {value}")
        else:
            info.append("- No standard EXIF tags found.")
            
        # Check EOF trailer data
        data = p.read_bytes()
        if img.format == "JPEG":
            # Check after FFD9 (EOF)
            eof_pos = data.find(b"\xff\xd9")
            if eof_pos != -1 and eof_pos + 2 < len(data):
                extra_bytes = len(data) - (eof_pos + 2)
                info.append(f"\n\u26a0\ufe0f **Alert:** Found {extra_bytes} bytes appended after the JPEG EOF trailer!")
                # Attempt to extract readable string from trailer
                trailer = data[eof_pos+2:]
                printable = re.findall(br'[ -~]{4,}', trailer)
                if printable:
                    trailer_strings = [s.decode("ascii", errors="ignore") for s in printable]
                    info.append(f"  * Printable trailer ASCII: {', '.join(trailer_strings)}")
        elif img.format == "PNG":
            # Check after IEND marker (49454e44ae426082)
            iend_pos = data.find(b"IEND")
            if iend_pos != -1 and iend_pos + 8 < len(data):
                extra_bytes = len(data) - (iend_pos + 8)
                info.append(f"\n\u26a0\ufe0f **Alert:** Found {extra_bytes} bytes appended after the PNG IEND chunk!")
                
        return "\n".join(info)
    except Exception as e:
        return f"Failed to perform stego metadata check: {e}"

def ctf_hint(challenge_type: str) -> str:
    """Provides learning strategies and steps for standard CTF categories."""
    ct = challenge_type.lower().strip()
    
    if "crypto" in ct:
        return (
            "**Crypto CTF Strategy:**\n"
            "1. Identify the cipher type (frequencies, encoding signatures, length).\n"
            "2. If it's character shifts: run a Caesar brute-force or ROT13 tool.\n"
            "3. If it looks like base64 or hex, decode it to view plaintext.\n"
            "4. For advanced ciphers (RSA, Vigenere), use tools like CyberChef or dcode.fr."
        )
    elif "steg" in ct:
        return (
            "**Steganography CTF Strategy:**\n"
            "1. Inspect file metadata (EXIF details) or EOF trailers for appended strings.\n"
            "2. Run strings to check if flag strings are embedded directly.\n"
            "3. Use tools like `binwalk` to verify if other files are packed inside the image.\n"
            "4. Analyze color bitplanes using StegSolve."
        )
    elif "web" in ct:
        return (
            "**Web Security CTF Strategy:**\n"
            "1. Check the browser source code (Inspect Element) for hidden comments or flags.\n"
            "2. Inspect the cookie storage and local parameters.\n"
            "3. Check for files like `robots.txt`, `.git/`, or `.env` exposed in root folders.\n"
            "4. Identify backend technologies and check for known parameter injection points."
        )
    elif "rev" in ct or "reverse" in ct:
        return (
            "**Reverse Engineering Strategy:**\n"
            "1. Run the `strings` command first to check for hardcoded flag templates.\n"
            "2. Use the `file` command to identify binary architectures and systems.\n"
            "3. Open the binary in decompilers like Ghidra, IDA Pro, or Cutter.\n"
            "4. Run under a debugger (GDB or x64dbg) to set breakpoints near input check branches."
        )
    else:
        return (
            f"No specific guidelines for '{challenge_type}'. Common CTF categories:\n"
            "- Cryptography\n- Steganography\n- Web Exploitation\n- Reverse Engineering\n- Binary Exploitation (Pwn)"
        )

def ctf_helper(parameters: dict[str, Any], player: Any = None) -> str:
    """
    Main orchestrator for CTF helper.
    """
    action = parameters.get("action", "").lower().strip()
    text = parameters.get("text", "")
    file_path = parameters.get("file_path", "")
    
    if action == "decode_base64":
        return decode_base64(text)
    elif action == "decode_hex":
        return decode_hex(text)
    elif action == "decode_rot13":
        return decode_rot13(text)
    elif action == "decode_morse":
        return decode_morse(text)
    elif action == "crack_caesar":
        return crack_caesar_cipher(text)
    elif action == "detect_encoding":
        return detect_encoding(text)
    elif action == "hash_identifier":
        return hash_identifier(text)
    elif action == "extract_strings":
        return extract_strings(file_path)
    elif action == "stego_check":
        return steganography_check(file_path)
    elif action == "hint":
        return ctf_hint(text)
    else:
        return f"Unknown ctf_helper action '{action}'."
