from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from saturnix_harness.config import Settings


class SecretCipher:
    """Small envelope cipher for local MVP secret storage.

    This uses a derived HMAC-SHA256 keystream so API keys are never stored as
    plaintext. Production deployments should replace this with KMS or Fernet.
    """

    def __init__(self, settings: Settings) -> None:
        configured = (
            settings.saturnix_dashboard_encryption_key.get_secret_value()
            if settings.saturnix_dashboard_encryption_key
            else ""
        )
        seed = configured or "saturnix-local-dev-change-me"
        self._key = hashlib.sha256(seed.encode("utf-8")).digest()

    def encrypt(self, plaintext: str) -> str:
        nonce = secrets.token_bytes(16)
        data = plaintext.encode("utf-8")
        stream = _keystream(self._key, nonce, len(data))
        ciphertext = bytes(left ^ right for left, right in zip(data, stream, strict=False))
        tag = hmac.new(self._key, nonce + ciphertext, hashlib.sha256).digest()
        payload = nonce + tag + ciphertext
        return base64.urlsafe_b64encode(payload).decode("ascii")

    def decrypt(self, token: str) -> str:
        payload = base64.urlsafe_b64decode(token.encode("ascii"))
        nonce = payload[:16]
        tag = payload[16:48]
        ciphertext = payload[48:]
        expected = hmac.new(self._key, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(tag, expected):
            raise ValueError("Encrypted secret failed integrity check.")
        stream = _keystream(self._key, nonce, len(ciphertext))
        data = bytes(left ^ right for left, right in zip(ciphertext, stream, strict=False))
        return data.decode("utf-8")


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < length:
        block = hmac.new(
            key,
            nonce + counter.to_bytes(8, "big"),
            hashlib.sha256,
        ).digest()
        output.extend(block)
        counter += 1
    return bytes(output[:length])
