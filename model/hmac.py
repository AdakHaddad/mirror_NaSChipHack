"""
HMAC-SHA-256 reference implementation (RFC 2104 / RFC 4231).
Uses our pure-Python SHA-256 so logic maps 1:1 to RTL.
"""

from .sha256 import sha256

BLOCK_SIZE = 64   # SHA-256 block size in bytes
HASH_SIZE = 32    # SHA-256 output size in bytes


def hmac_sha256(key: bytes, message: bytes) -> bytes:
    """
    Compute HMAC-SHA-256(key, message). Returns 32 bytes.

    RTL mapping:
      1. Key preparation     → key_vault or ro_puf output
      2. ipad XOR + hash     → first SHA-256 block processing
      3. opad XOR + hash     → second SHA-256 block processing
    """
    # Step 1: Key preparation
    if len(key) > BLOCK_SIZE:
        key = sha256(key)  # Hash long keys
    key = key.ljust(BLOCK_SIZE, b'\x00')  # Pad short keys with zeros

    # Step 2: Inner hash = SHA-256(K XOR ipad || message)
    ipad = bytes(k ^ 0x36 for k in key)
    inner = sha256(ipad + message)

    # Step 3: Outer hash = SHA-256(K XOR opad || inner_hash)
    opad = bytes(k ^ 0x5C for k in key)
    outer = sha256(opad + inner)

    return outer


def hmac_sha256_hex(key: bytes, message: bytes) -> str:
    """Return HMAC-SHA-256 as hex string."""
    return hmac_sha256(key, message).hex()
