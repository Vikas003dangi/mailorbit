import base64
import pytest
from cryptography.exceptions import InvalidTag
from apps.api.config import settings
from packages.shared.crypto import EncryptionService, EnvKeyManager


def test_encryption_lifecycle():
    key_mgr = EnvKeyManager(settings.ENCRYPTION_MASTER_KEY)
    service = EncryptionService(key_mgr)

    secret = "mo_relay_sec_7f9b8c2d1e0a"
    encrypted1 = service.encrypt(secret)
    encrypted2 = service.encrypt(secret)

    # Must have v1 prefix
    assert encrypted1.startswith("v1:")
    assert encrypted2.startswith("v1:")

    # Must produce different ciphertext due to random IV/nonce
    assert encrypted1 != encrypted2

    # Must decrypt back to original secret
    assert service.decrypt(encrypted1) == secret
    assert service.decrypt(encrypted2) == secret


def test_tampered_ciphertext_fails():
    key_mgr = EnvKeyManager(settings.ENCRYPTION_MASTER_KEY)
    service = EncryptionService(key_mgr)

    secret = "my-secret-key"
    encrypted = service.encrypt(secret)

    # Tamper with the raw payload bytes (flip a bit in the encrypted payload)
    raw = bytearray(base64.b64decode(encrypted[3:]))
    raw[15] ^= 0xFF  # Flip byte in ciphertext/tag
    tampered = "v1:" + base64.b64encode(raw).decode("ascii")

    with pytest.raises(InvalidTag):
        service.decrypt(tampered)


def test_mask_secret():
    secret = "sec_orbit_test_7f21a"
    masked = EncryptionService.mask_secret(secret, visible_suffix_len=5)
    assert masked == "••••••••7f21a"
    assert "orbit" not in masked
