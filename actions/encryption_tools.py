"""
actions/encryption_tools.py — Local File and Text Encryption Toolkit.

Provides AES-256 file encryption, text encryption, RSA asymmetric keypair
generation, digital signatures, and cryptographic validation.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("ip_prime.encryption_tools")

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logger.warning("cryptography package is not installed. Cryptographic operations will fail.")

def _derive_key(password: str, salt: bytes = b"ipprime_fixed_salt") -> bytes:
    """Derives a cryptographically secure 32-byte key from a text password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))

def encrypt_file(file_path: str, password: str, player: Any = None) -> str:
    """Encrypts a local file using AES via the Fernet protocol."""
    if not CRYPTOGRAPHY_AVAILABLE:
        return "Error: cryptography package is missing. Run pip install cryptography."
        
    p = Path(file_path).resolve()
    if not p.exists() or not p.is_file():
        return f"Target file not found at: {file_path}"
        
    try:
        data = p.read_bytes()
        key = _derive_key(password)
        fernet = Fernet(key)
        encrypted = fernet.encrypt(data)
        
        # Save as .enc file
        enc_path = p.with_suffix(p.suffix + ".enc")
        enc_path.write_bytes(encrypted)
        return f"\u2705 **File Encrypted Successfully!**\nSaved encrypted file to: {enc_path.name}"
    except Exception as e:
        return f"Encryption failed: {e}"

def decrypt_file(file_path: str, password: str, player: Any = None) -> str:
    """Decrypts a local .enc file back to its original representation."""
    if not CRYPTOGRAPHY_AVAILABLE:
        return "Error: cryptography package is missing."
        
    p = Path(file_path).resolve()
    if not p.exists() or not p.is_file():
        return f"Target file not found at: {file_path}"
        
    try:
        data = p.read_bytes()
        key = _derive_key(password)
        fernet = Fernet(key)
        decrypted = fernet.decrypt(data)
        
        # Save output without .enc extension
        out_name = p.name.replace(".enc", "")
        out_path = p.parent / f"decrypted_{out_name}"
        out_path.write_bytes(decrypted)
        return f"\u2705 **File Decrypted Successfully!**\nSaved decrypted file to: {out_path.name}"
    except Exception as e:
        return f"Decryption failed. Please verify password correctness. Error: {e}"

def generate_rsa_keypair(output_dir: str = "", player: Any = None) -> str:
    """Generates an RSA asymmetric private and public keypair securely."""
    if not CRYPTOGRAPHY_AVAILABLE:
        return "Error: cryptography package is missing."
        
    out = Path(output_dir).resolve() if output_dir else Path.home() / ".ipprime" / "keys"
    out.mkdir(parents=True, exist_ok=True)
    
    try:
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        # Serialize Private Key
        pem_private = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize Public Key
        public_key = private_key.public_key()
        pem_public = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        priv_file = out / "rsa_private.pem"
        pub_file = out / "rsa_public.pem"
        
        priv_file.write_bytes(pem_private)
        pub_file.write_bytes(pem_public)
        
        return (
            f"\u2705 **RSA Keypair Generated successfully!**\n"
            f"- Private Key: {priv_file.name} (Keep this secure!)\n"
            f"- Public Key: {pub_file.name} (Share this with others)\n"
            f"Saved keys inside folder: {out}"
        )
    except Exception as e:
        return f"Failed to generate RSA keypair: {e}"

def sign_file(file_path: str, private_key_path: str, player: Any = None) -> str:
    """Digitally signs a local file using an RSA private key."""
    if not CRYPTOGRAPHY_AVAILABLE:
        return "Error: cryptography package is missing."
        
    fp = Path(file_path).resolve()
    kp = Path(private_key_path).resolve()
    
    if not fp.exists() or not fp.is_file():
        return f"File to sign not found: {file_path}"
    if not kp.exists() or not kp.is_file():
        return f"Private key not found: {private_key_path}"
        
    try:
        # Load Private Key
        priv_bytes = kp.read_bytes()
        private_key = serialization.load_pem_private_key(priv_bytes, password=None)
        
        # Read file data
        data = fp.read_bytes()
        
        # Generate Signature
        signature = private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Save signature as .sig
        sig_file = fp.with_suffix(fp.suffix + ".sig")
        sig_file.write_bytes(signature)
        return f"\u2705 **File Signed successfully!**\nSaved digital signature as: {sig_file.name}"
    except Exception as e:
        return f"Failed to sign file: {e}"

def verify_signature(file_path: str, public_key_path: str, signature_path: str, player: Any = None) -> str:
    """Verifies a file's digital signature using an RSA public key."""
    if not CRYPTOGRAPHY_AVAILABLE:
        return "Error: cryptography package is missing."
        
    fp = Path(file_path).resolve()
    kp = Path(public_key_path).resolve()
    sp = Path(signature_path).resolve()
    
    if not fp.exists() or not fp.is_file():
        return f"File to verify not found: {file_path}"
    if not kp.exists() or not kp.is_file():
        return f"Public key not found: {public_key_path}"
    if not sp.exists() or not sp.is_file():
        return f"Signature file not found: {signature_path}"
        
    try:
        # Load Public Key
        pub_bytes = kp.read_bytes()
        public_key = serialization.load_pem_public_key(pub_bytes)
        
        # Read files
        data = fp.read_bytes()
        signature = sp.read_bytes()
        
        # Verify
        public_key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return "\u2705 **Success! Digital signature is VALID.** The file contents have not been modified."
    except Exception as e:
        return f"\u274c **Invalid Signature!** Verification failed. The file may have been altered. Error: {e}"

def encryption_tools(parameters: dict[str, Any], player: Any = None) -> str:
    """
    Main orchestrator for encryption tools.
    """
    action = parameters.get("action", "").lower().strip()
    path = parameters.get("path", "")
    password = parameters.get("password", "")
    key_path = parameters.get("key_path", "")
    sig_path = parameters.get("sig_path", "")
    
    if action == "encrypt":
        return encrypt_file(path, password, player)
    elif action == "decrypt":
        return decrypt_file(path, password, player)
    elif action == "generate_rsa":
        return generate_rsa_keypair(path, player)
    elif action == "sign":
        return sign_file(path, key_path, player)
    elif action == "verify":
        return verify_signature(path, key_path, sig_path, player)
    else:
        return f"Unknown encryption_tools action '{action}'."
