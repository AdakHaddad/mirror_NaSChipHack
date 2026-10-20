"""
Test vector generator for RTL verification.

Outputs JSON files that cocotb testbenches consume to verify
SHA-256 and HMAC-SHA-256 cores match the Python reference model.

Vectors include:
  1. FIPS 180-4 SHA-256 known-answer tests
  2. RFC 4231 HMAC-SHA-256 known-answer tests
  3. SeBatt protocol vectors (nonce + id + voltage → HMAC)
  4. History vectors (0x53 record tag and 0x48 summary tag)
"""

import json
import os
import struct
from pathlib import Path

from .sha256 import sha256_hex
from .hmac import hmac_sha256, hmac_sha256_hex
from .protocol import (
    AUTH_MSG_PREFIX, RECORD_MSG_PREFIX, SUMMARY_MSG_PREFIX,
)


def fips_sha256_vectors() -> list[dict]:
    """
    FIPS 180-4 Section B.1–B.3 test vectors for SHA-256.
    """
    vectors = []

    # B.1: one-block message "abc"
    vectors.append({
        'id': 'FIPS-B1',
        'msg_hex': b'abc'.hex(),
        'hash_hex': 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
    })

    # B.2: two-block message
    msg_b2 = b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq'
    vectors.append({
        'id': 'FIPS-B2',
        'msg_hex': msg_b2.hex(),
        'hash_hex': '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1',
    })

    # B.3: long message (1 million 'a' characters) — skip for RTL, too slow
    # vectors.append({
    #     'id': 'FIPS-B3',
    #     'msg_hex': (b'a' * 1_000_000).hex(),
    #     'hash_hex': 'cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0',
    # })

    # Verify our implementation matches
    for v in vectors:
        computed = sha256_hex(bytes.fromhex(v['msg_hex']))
        assert computed == v['hash_hex'], \
            f"SHA-256 mismatch on {v['id']}: {computed} != {v['hash_hex']}"

    return vectors


def rfc4231_hmac_vectors() -> list[dict]:
    """
    RFC 4231 test vectors for HMAC-SHA-256.
    """
    vectors = []

    # Test Case 1
    vectors.append({
        'id': 'RFC4231-1',
        'key_hex': '0b' * 20,
        'msg_hex': bytes(b'Hi There').hex(),
        'mac_hex': 'b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7',
    })

    # Test Case 2: "Jefe"
    vectors.append({
        'id': 'RFC4231-2',
        'key_hex': bytes(b'Jefe').hex(),
        'msg_hex': bytes(b'what do ya want for nothing?').hex(),
        'mac_hex': '5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843',
    })

    # Test Case 3
    vectors.append({
        'id': 'RFC4231-3',
        'key_hex': 'aa' * 20,
        'msg_hex': 'dd' * 50,
        'mac_hex': '773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe',
    })

    # Test Case 4
    vectors.append({
        'id': 'RFC4231-4',
        'key_hex': '0102030405060708090a0b0c0d0e0f10111213141516171819',
        'msg_hex': 'cd' * 50,
        'mac_hex': '82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b',
    })

    # Test Case 6: key > block size
    vectors.append({
        'id': 'RFC4231-6',
        'key_hex': 'aa' * 131,
        'msg_hex': bytes(b'Test Using Larger Than Block-Size Key - Hash Key First').hex(),
        'mac_hex': '60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54',
    })

    # Test Case 7: key > block size, longer message
    vectors.append({
        'id': 'RFC4231-7',
        'key_hex': 'aa' * 131,
        'msg_hex': bytes(
            b'This is a test using a larger than block-size ke'
            b'y and a larger than block-size data. The key nee'
            b'ds to be hashed before being used by the HMAC algorithm.'
        ).hex(),
        'mac_hex': '9b09ffa71b942fcb27635fbcd5b0e944bfdc63644f0713938a7f51535c3a35e2',
    })

    # Verify
    for v in vectors:
        key = bytes.fromhex(v['key_hex'])
        msg = bytes.fromhex(v['msg_hex'])
        computed = hmac_sha256_hex(key, msg)
        assert computed == v['mac_hex'], \
            f"HMAC mismatch on {v['id']}: {computed} != {v['mac_hex']}"

    return vectors


def sebatt_protocol_vectors(count: int = 20) -> list[dict]:
    """
    SeBatt-specific test vectors for full protocol verification.
    message = 0x41 || nonce(32) || battery_id(4) || voltage(2)  (prefix: spec
    section 6). Each entry also carries one 0x53 record and one 0x48 summary
    vector so the same MAC core can be checked against the stored-tag path.
    """
    vectors = []

    # Fixed key (stage 1 — key_vault)
    key = bytes(range(32))

    for i in range(count):
        # Deterministic for reproducibility
        nonce = bytes([(i * 7 + j) & 0xFF for j in range(32)])
        battery_id = struct.pack('>I', 0x42415400 + i)  # "BAT\x00" + i
        voltage = 3000 + i * 50  # 3000–3950 mV range
        voltage_bytes = struct.pack('>H', voltage)

        message = (bytes([AUTH_MSG_PREFIX]) + nonce + battery_id
                   + voltage_bytes)
        mac = hmac_sha256(key, message)

        seq = i
        record_msg = (bytes([RECORD_MSG_PREFIX]) + battery_id
                      + struct.pack('>IH', seq, voltage))
        record_mac = hmac_sha256(key, record_msg)

        summary_nonce = bytes([(i * 11 + j) & 0xFF for j in range(32)])
        summary_msg = (bytes([SUMMARY_MSG_PREFIX]) + summary_nonce
                       + battery_id + struct.pack('>II', seq, seq))
        summary_mac = hmac_sha256(key, summary_msg)

        vectors.append({
            'id': f'SEBATT-{i:03d}',
            'key_hex': key.hex(),
            'nonce_hex': nonce.hex(),
            'battery_id_hex': battery_id.hex(),
            'voltage': voltage,
            'msg_hex': message.hex(),
            'mac_hex': mac.hex(),
            'record_seq': seq,
            'record_msg_hex': record_msg.hex(),
            'record_mac_hex': record_mac.hex(),
            'summary_nonce_hex': summary_nonce.hex(),
            'summary_msg_hex': summary_msg.hex(),
            'summary_mac_hex': summary_mac.hex(),
        })

    return vectors


def generate_all(output_dir: str = None):
    """Generate all test vector files."""
    if output_dir is None:
        output_dir = str(Path(__file__).parent / 'vectors')

    os.makedirs(output_dir, exist_ok=True)

    # SHA-256 vectors
    sha_vecs = fips_sha256_vectors()
    with open(os.path.join(output_dir, 'sha256_vectors.json'), 'w') as f:
        json.dump(sha_vecs, f, indent=2)
    print(f"[OK] {len(sha_vecs)} SHA-256 vectors → sha256_vectors.json")

    # HMAC-SHA-256 vectors
    hmac_vecs = rfc4231_hmac_vectors()
    with open(os.path.join(output_dir, 'hmac_vectors.json'), 'w') as f:
        json.dump(hmac_vecs, f, indent=2)
    print(f"[OK] {len(hmac_vecs)} HMAC-SHA-256 vectors → hmac_vectors.json")

    # SeBatt protocol vectors
    proto_vecs = sebatt_protocol_vectors()
    with open(os.path.join(output_dir, 'protocol_vectors.json'), 'w') as f:
        json.dump(proto_vecs, f, indent=2)
    print(f"[OK] {len(proto_vecs)} protocol vectors → protocol_vectors.json")

    # Also generate .mem format for Verilog $readmemh
    _write_memfiles(sha_vecs, hmac_vecs, proto_vecs, output_dir)

    print(f"\nAll vectors written to {output_dir}/")


def _write_memfiles(sha_vecs, hmac_vecs, proto_vecs, output_dir):
    """
    Write .mem files for Verilog $readmemh testbenches.
    Format: one hex word per line, 32-bit big-endian.
    """
    mem_dir = os.path.join(output_dir, 'mem')
    os.makedirs(mem_dir, exist_ok=True)

    # SHA-256: each vector = message words + expected hash words
    for v in sha_vecs:
        name = v['id'].lower().replace('-', '_')
        msg_bytes = bytes.fromhex(v['msg_hex'])
        hash_bytes = bytes.fromhex(v['hash_hex'])

        # Pad message to block boundary (SHA-256 padding)
        from .sha256 import _pad
        padded = _pad(msg_bytes)

        with open(os.path.join(mem_dir, f'{name}_msg.mem'), 'w') as f:
            for i in range(0, len(padded), 4):
                word = struct.unpack('>I', padded[i:i+4])[0]
                f.write(f'{word:08x}\n')

        with open(os.path.join(mem_dir, f'{name}_hash.mem'), 'w') as f:
            for i in range(0, 32, 4):
                word = struct.unpack('>I', hash_bytes[i:i+4])[0]
                f.write(f'{word:08x}\n')

    # HMAC: key + message + expected MAC
    for v in hmac_vecs:
        name = v['id'].lower().replace('-', '_')
        key_bytes = bytes.fromhex(v['key_hex'])
        msg_bytes = bytes.fromhex(v['msg_hex'])
        mac_bytes = bytes.fromhex(v['mac_hex'])

        with open(os.path.join(mem_dir, f'{name}_key.mem'), 'w') as f:
            # Pad key to 64 bytes (block size)
            if len(key_bytes) > 64:
                from .sha256 import sha256
                key_bytes = sha256(key_bytes)
            key_padded = key_bytes.ljust(64, b'\x00')
            for i in range(0, 64, 4):
                word = struct.unpack('>I', key_padded[i:i+4])[0]
                f.write(f'{word:08x}\n')

        with open(os.path.join(mem_dir, f'{name}_msg.mem'), 'w') as f:
            # Pad message to 4-byte boundary
            padded_msg = msg_bytes + b'\x00' * ((4 - len(msg_bytes) % 4) % 4)
            for i in range(0, len(padded_msg), 4):
                word = struct.unpack('>I', padded_msg[i:i+4])[0]
                f.write(f'{word:08x}\n')

        with open(os.path.join(mem_dir, f'{name}_mac.mem'), 'w') as f:
            for i in range(0, 32, 4):
                word = struct.unpack('>I', mac_bytes[i:i+4])[0]
                f.write(f'{word:08x}\n')

    print(f"[OK] .mem files for Verilog $readmemh → {mem_dir}/")


if __name__ == '__main__':
    generate_all()
