import base64
import os
from typing import Protocol
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class KeyManagerProtocol(Protocol):
    def get_master_key(self) -> bytes:
        ...


class EnvKeyManager:
    """
    Key Manager that retrieves the master key from environment variables.
    Provides a clean, modular abstraction so cloud KMS (AWS KMS, GCP KMS)
    can be swapped in later without modifying any encryption/decryption callers.
    """

    def __init__(self, key_b64: str):
        if not key_b64:
            raise ValueError("ENCRYPTION_MASTER_KEY must not be empty")
        raw = base64.b64decode(key_b64)
        if len(raw) != 32:
            raise ValueError(f"Master key must be exactly 32 bytes (AES-256), got {len(raw)} bytes")
        self._key = raw

    def get_master_key(self) -> bytes:
        return self._key


class EncryptionService:
    """
    AES-256-GCM Authenticated Encryption Service.
    Protects user credentials (Gmail Apps Script relay tokens, Gemini API keys) at rest.
    Format: v1:{base64(12-byte-nonce + ciphertext + 16-byte-tag)}
    """

    VERSION_PREFIX = "v1:"

    def __init__(self, key_manager: KeyManagerProtocol):
        self.key_manager = key_manager

    def encrypt(self, plaintext: str) -> str:
        """Encrypts plaintext string using AES-256-GCM with a fresh 12-byte random nonce."""
        if not plaintext:
            return ""
        key = self.key_manager.get_master_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        encrypted_bytes = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        payload = nonce + encrypted_bytes
        encoded = base64.b64encode(payload).decode("ascii")
        return f"{self.VERSION_PREFIX}{encoded}"

    def decrypt(self, ciphertext_envelope: str) -> str:
        """Decrypts a v1 ciphertext envelope back to plaintext string."""
        if not ciphertext_envelope:
            return ""
        if not ciphertext_envelope.startswith(self.VERSION_PREFIX):
            raise ValueError("Invalid ciphertext envelope format: missing version prefix")
        
        encoded = ciphertext_envelope[len(self.VERSION_PREFIX):]
        payload = base64.b64decode(encoded)
        if len(payload) < 28: # 12 bytes nonce + 16 bytes tag
            raise ValueError("Ciphertext payload too short")
            
        nonce = payload[:12]
        data = payload[12:]
        key = self.key_manager.get_master_key()
        aesgcm = AESGCM(key)
        decrypted_bytes = aesgcm.decrypt(nonce, data, None)
        return decrypted_bytes.decode("utf-8")

    @staticmethod
    def mask_secret(secret: str, visible_suffix_len: int = 4) -> str:
        """Returns a safe, masked representation of a secret (e.g. '••••••••7f21a')."""
        if not secret:
            return ""
        if len(secret) <= visible_suffix_len:
            return "•" * len(secret)
        return "•" * 8 + secret[-visible_suffix_len:]
