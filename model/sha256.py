"""
Pure-Python SHA-256 reference implementation.
Matches FIPS 180-4 exactly. Written for clarity so the logic maps
directly to the RTL we build on Day 2.

No external dependencies — stdlib only.
"""

import struct

# --- Constants (first 32 bits of fractional parts of cube roots of first 64 primes) ---
K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]

# Initial hash values (first 32 bits of fractional parts of square roots of first 8 primes)
H_INIT = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]

MASK32 = 0xFFFFFFFF


def _rotr(x: int, n: int) -> int:
    """32-bit right rotate."""
    return ((x >> n) | (x << (32 - n))) & MASK32


def _shr(x: int, n: int) -> int:
    """32-bit right shift."""
    return (x >> n) & MASK32


def _ch(x: int, y: int, z: int) -> int:
    return (x & y) ^ (~x & z) & MASK32


def _maj(x: int, y: int, z: int) -> int:
    return (x & y) ^ (x & z) ^ (y & z)


def _sigma0(x: int) -> int:
    return _rotr(x, 2) ^ _rotr(x, 13) ^ _rotr(x, 22)


def _sigma1(x: int) -> int:
    return _rotr(x, 6) ^ _rotr(x, 11) ^ _rotr(x, 25)


def _gamma0(x: int) -> int:
    return _rotr(x, 7) ^ _rotr(x, 18) ^ _shr(x, 3)


def _gamma1(x: int) -> int:
    return _rotr(x, 17) ^ _rotr(x, 19) ^ _shr(x, 10)


def _pad(message: bytes) -> bytes:
    """SHA-256 padding: append 1-bit, zeros, then 64-bit big-endian length."""
    mlen = len(message)
    bit_len = mlen * 8
    # Append 0x80 byte
    message += b'\x80'
    # Pad with zeros until length = 56 mod 64
    message += b'\x00' * ((56 - (mlen + 1) % 64) % 64)
    # Append original length as 64-bit big-endian
    message += struct.pack('>Q', bit_len)
    return message


def sha256(message: bytes) -> bytes:
    """Compute SHA-256 hash of message. Returns 32 bytes."""
    padded = _pad(message)
    assert len(padded) % 64 == 0

    h = list(H_INIT)

    # Process each 512-bit (64-byte) block
    for block_start in range(0, len(padded), 64):
        block = padded[block_start:block_start + 64]

        # Prepare message schedule W[0..63]
        w = list(struct.unpack('>16I', block))
        for i in range(16, 64):
            w.append(
                (_gamma1(w[i - 2]) + w[i - 7] + _gamma0(w[i - 15]) + w[i - 16]) & MASK32
            )

        # Working variables
        a, b, c, d, e, f, g, hh = h

        # 64 rounds
        for i in range(64):
            t1 = (hh + _sigma1(e) + _ch(e, f, g) + K[i] + w[i]) & MASK32
            t2 = (_sigma0(a) + _maj(a, b, c)) & MASK32
            hh = g
            g = f
            f = e
            e = (d + t1) & MASK32
            d = c
            c = b
            b = a
            a = (t1 + t2) & MASK32

        # Add compressed chunk to hash value
        h = [(x + y) & MASK32 for x, y in zip(h, [a, b, c, d, e, f, g, hh])]

    return struct.pack('>8I', *h)


def sha256_hex(message: bytes) -> str:
    """Return SHA-256 hash as hex string."""
    return sha256(message).hex()


# --- Block-level interface for HMAC (matches RTL processing) ---

class SHA256Core:
    """
    Stateful SHA-256 that exposes block-level processing.
    Maps to how RTL core processes blocks sequentially.
    """

    def __init__(self):
        self.h = list(H_INIT)
        self.buffer = b''
        self.total_len = 0

    def update(self, data: bytes):
        """Feed data. Processes complete 64-byte blocks immediately."""
        self.buffer += data
        self.total_len += len(data)
        while len(self.buffer) >= 64:
            self._process_block(self.buffer[:64])
            self.buffer = self.buffer[64:]

    def _process_block(self, block: bytes):
        """Process single 512-bit block. Mirrors RTL compression."""
        assert len(block) == 64
        w = list(struct.unpack('>16I', block))
        for i in range(16, 64):
            w.append(
                (_gamma1(w[i - 2]) + w[i - 7] + _gamma0(w[i - 15]) + w[i - 16]) & MASK32
            )
        a, b, c, d, e, f, g, hh = self.h
        for i in range(64):
            t1 = (hh + _sigma1(e) + _ch(e, f, g) + K[i] + w[i]) & MASK32
            t2 = (_sigma0(a) + _maj(a, b, c)) & MASK32
            hh = g
            g = f
            f = e
            e = (d + t1) & MASK32
            d = c
            c = b
            b = a
            a = (t1 + t2) & MASK32
        self.h = [(x + y) & MASK32 for x, y in zip(self.h, [a, b, c, d, e, f, g, hh])]

    def digest(self) -> bytes:
        """Finalize and return 32-byte hash. Does not modify state."""
        # Work on copy so digest() is idempotent
        buf = self.buffer
        total = self.total_len
        bit_len = total * 8
        buf += b'\x80'
        buf += b'\x00' * ((56 - len(buf) % 64) % 64)
        buf += struct.pack('>Q', bit_len)

        h = list(self.h)
        for block_start in range(0, len(buf), 64):
            block = buf[block_start:block_start + 64]
            w = list(struct.unpack('>16I', block))
            for i in range(16, 64):
                w.append(
                    (_gamma1(w[i - 2]) + w[i - 7] + _gamma0(w[i - 15]) + w[i - 16]) & MASK32
                )
            a, b, c, d, e, f, g, hh = h
            for i in range(64):
                t1 = (hh + _sigma1(e) + _ch(e, f, g) + K[i] + w[i]) & MASK32
                t2 = (_sigma0(a) + _maj(a, b, c)) & MASK32
                hh = g
                g = f
                f = e
                e = (d + t1) & MASK32
                d = c
                c = b
                b = a
                a = (t1 + t2) & MASK32
            h = [(x + y) & MASK32 for x, y in zip(h, [a, b, c, d, e, f, g, hh])]

        return struct.pack('>8I', *h)

    def hexdigest(self) -> str:
        return self.digest().hex()
