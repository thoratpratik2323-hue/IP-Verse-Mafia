import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Derived standard fixed key for local data encryption
_PASSWORD = b"ip_prime_system_local_encryption_key_2026"
_SALT = b"ip_prime_salt_99"

kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=_SALT,
    iterations=100000
)
_KEY = base64.urlsafe_b64encode(kdf.derive(_PASSWORD))
_fernet = Fernet(_KEY)

def encrypt_string(text: str) -> str:
    """Encrypts a plaintext string and returns a base64 encoded ciphertext string."""
    if not text:
        return ""
    try:
        return _fernet.encrypt(text.encode("utf-8")).decode("utf-8")
    except Exception:
        return text

def decrypt_string(ciphertext: str) -> str:
    """Decrypts a base64 encoded ciphertext string back to plaintext."""
    if not ciphertext:
        return ""
    try:
        return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except Exception:
        return ciphertext
