"""
core/crypto_utils.py
Enterprise cryptographic services using the official 'cryptography' library:
1. In-Memory Credential Protection:
   - Uses Fernet (AES-128-CBC with HMAC-SHA256 authenticated encryption)
   - Ephemeral session key generated per process lifecycle
   - Protects credentials against process memory scraping and unintentional dumps
2. Cryptographic Integrity Verifications:
   - SHA-256 cryptographic hash computation and validation
   - Remote bash probe generation for cryptographic artifact verification (sha256sum)
"""
import hashlib
import os
from typing import Optional, Union
from cryptography.fernet import Fernet, InvalidToken

class SessionCrypto:
    """Manages ephemeral in-memory encryption for sensitive data such as SSH passwords."""
    _instance: Optional['SessionCrypto'] = None
    _fernet: Optional[Fernet] = None

    def __init__(self):
        # Generate a unique ephemeral 32-byte URL-safe base64-encoded key per session
        self._key = Fernet.generate_key()
        self._fernet = Fernet(self._key)

    @classmethod
    def get_instance(cls) -> 'SessionCrypto':
        if cls._instance is None:
            cls._instance = SessionCrypto()
        return cls._instance

    def encrypt_secret(self, plaintext: str) -> bytes:
        """Encrypt a secret string into an authenticated ciphertext token."""
        if not plaintext:
            return b""
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def decrypt_secret(self, token: bytes) -> str:
        """Decrypt an authenticated ciphertext token back to plaintext."""
        if not token:
            return ""
        try:
            return self._fernet.decrypt(token).decode("utf-8")
        except InvalidToken:
            return ""

def encrypt_in_memory(secret: str) -> bytes:
    """Helper to encrypt sensitive strings for secure in-memory retention."""
    return SessionCrypto.get_instance().encrypt_secret(secret)

def decrypt_in_memory(token: bytes) -> str:
    """Helper to decrypt sensitive strings when needed for authentication."""
    return SessionCrypto.get_instance().decrypt_secret(token)

def compute_sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 cryptographic hash of byte array."""
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest().lower()

def compute_sha256_file(file_path: str) -> Optional[str]:
    """Compute SHA-256 cryptographic hash of a local file."""
    if not os.path.isfile(file_path):
        return None
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()

def verify_hash(actual_hash: str, expected_hash: str) -> bool:
    """Cryptographically constant-time comparison of two hashes."""
    if not actual_hash or not expected_hash:
        return False
    import hmac
    return hmac.compare_digest(actual_hash.strip().lower(), expected_hash.strip().lower())

def build_sha256_remote_probe(file_path: str) -> str:
    """Generate remote bash command to calculate cryptographic SHA-256 checksum."""
    import shlex
    clean = str(file_path).strip().replace("\r", "").replace("\n", "").replace("\0", "")
    safe_p = shlex.quote(clean)
    return f"if [ -f {safe_p} ]; then sha256sum {safe_p} 2>/dev/null | awk '{{print $1}}'; else echo 'MISSING'; fi"
