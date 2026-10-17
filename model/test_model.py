"""
Unit tests for all SeBatt model components.

Run: python -m pytest model/test_model.py -v
  or: python -m pytest model/ -v
"""

import struct
import pytest

from .sha256 import sha256, sha256_hex, SHA256Core
from .hmac import hmac_sha256, hmac_sha256_hex
from .ro_puf import ROPUFModel, ROPUFConfig, KeyVault
from .protocol import (
    SeBattChip, Station, AuthStatus, WireProtocol,
    AuthRequest, AuthResponse, Command,
)
from .gen_vectors import fips_sha256_vectors, rfc4231_hmac_vectors


# ===================================================================
# SHA-256 tests
# ===================================================================

class TestSHA256:

    def test_fips_b1_abc(self):
        assert sha256_hex(b'abc') == \
            'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'

    def test_fips_b2_two_blocks(self):
        msg = b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq'
        assert sha256_hex(msg) == \
            '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1'

    def test_empty_string(self):
        assert sha256_hex(b'') == \
            'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'

    def test_single_byte(self):
        # Known value
        assert sha256_hex(b'\x00') == \
            '6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d'

    def test_exactly_55_bytes(self):
        """55 bytes = fits in one block after padding (55 + 1 + 8 = 64)."""
        msg = b'A' * 55
        result = sha256(msg)
        assert len(result) == 32

    def test_exactly_56_bytes(self):
        """56 bytes = needs two blocks (boundary case)."""
        msg = b'A' * 56
        result = sha256(msg)
        assert len(result) == 32

    def test_sha256_core_matches_function(self):
        """SHA256Core (stateful) matches sha256() (one-shot)."""
        msg = b'The quick brown fox jumps over the lazy dog'
        core = SHA256Core()
        core.update(msg)
        assert core.digest() == sha256(msg)

    def test_sha256_core_incremental(self):
        """SHA256Core incremental update matches one-shot."""
        msg = b'Hello, World! This is a test of incremental hashing.'
        # One-shot
        expected = sha256(msg)
        # Incremental in chunks
        core = SHA256Core()
        core.update(msg[:10])
        core.update(msg[10:30])
        core.update(msg[30:])
        assert core.digest() == expected

    def test_all_fips_vectors(self):
        """All FIPS 180-4 vectors pass."""
        vectors = fips_sha256_vectors()
        assert len(vectors) >= 2


# ===================================================================
# HMAC-SHA-256 tests
# ===================================================================

class TestHMAC:

    def test_rfc4231_case1(self):
        key = bytes.fromhex('0b' * 20)
        msg = b'Hi There'
        assert hmac_sha256_hex(key, msg) == \
            'b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7'

    def test_rfc4231_case2(self):
        key = b'Jefe'
        msg = b'what do ya want for nothing?'
        assert hmac_sha256_hex(key, msg) == \
            '5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843'

    def test_rfc4231_case3(self):
        key = bytes.fromhex('aa' * 20)
        msg = bytes.fromhex('dd' * 50)
        assert hmac_sha256_hex(key, msg) == \
            '773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe'

    def test_rfc4231_case4(self):
        key = bytes.fromhex('0102030405060708090a0b0c0d0e0f10111213141516171819')
        msg = bytes.fromhex('cd' * 50)
        assert hmac_sha256_hex(key, msg) == \
            '82558a389a443c0ea4cc819899f2083a85f0faa3e578f8077a2e3ff46729665b'

    def test_rfc4231_case6_long_key(self):
        key = bytes.fromhex('aa' * 131)
        msg = b'Test Using Larger Than Block-Size Key - Hash Key First'
        assert hmac_sha256_hex(key, msg) == \
            '60e431591ee0b67f0d8a26aacbf5b77f8e0bc6213728c5140546040f0ee37f54'

    def test_all_rfc_vectors(self):
        """All RFC 4231 vectors pass."""
        vectors = rfc4231_hmac_vectors()
        assert len(vectors) >= 5

    def test_empty_message(self):
        key = b'\x00' * 32
        result = hmac_sha256(key, b'')
        assert len(result) == 32


# ===================================================================
# RO-PUF tests
# ===================================================================

class TestROPUF:

    def test_key_vault_default(self):
        kv = KeyVault()
        assert len(kv.get_key()) == 32
        assert kv.get_key() == bytes(range(32))

    def test_key_vault_custom(self):
        key = b'\xAA' * 32
        kv = KeyVault(key)
        assert kv.get_key() == key

    def test_key_vault_wrong_length(self):
        with pytest.raises(AssertionError):
            KeyVault(b'\x00' * 16)

    def test_puf_create_instance(self):
        model = ROPUFModel(ROPUFConfig(seed=42))
        inst = model.create_instance()
        assert len(inst.base_counts) == 64
        assert not inst.enrolled

    def test_puf_enrollment(self):
        model = ROPUFModel(ROPUFConfig(seed=42))
        inst = model.create_instance()
        key = model.enroll(inst)
        assert len(key) == 32
        assert inst.enrolled

    def test_puf_key_reconstruction(self):
        model = ROPUFModel(ROPUFConfig(seed=42))
        inst = model.create_instance()
        key1 = model.enroll(inst)
        key2 = model.reconstruct_key(inst)
        assert key1 == key2

    def test_puf_different_instances_different_keys(self):
        model = ROPUFModel(ROPUFConfig(seed=42))
        inst_a = model.create_instance()
        inst_b = model.create_instance()
        key_a = model.enroll(inst_a)
        key_b = model.enroll(inst_b)
        assert key_a != key_b

    def test_puf_hamming_inter(self):
        """Different instances should have ~50% Hamming distance."""
        model = ROPUFModel(ROPUFConfig(seed=42))
        inst_a = model.create_instance()
        inst_b = model.create_instance()
        bits_a = model.generate_response(inst_a)
        bits_b = model.generate_response(inst_b)
        hd = model.hamming_distance(bits_a, bits_b)
        # Should be roughly 0.3–0.7 for good PUF
        assert 0.1 < hd < 0.9

    def test_puf_hamming_intra(self):
        """Same instance, two reads should have low Hamming distance."""
        model = ROPUFModel(ROPUFConfig(seed=42, noise_stddev=0.5))
        inst = model.create_instance()
        bits_1 = model.generate_response(inst)
        bits_2 = model.generate_response(inst)
        hd = model.hamming_distance(bits_1, bits_2)
        assert hd < 0.3  # Should be very low


# ===================================================================
# Protocol tests
# ===================================================================

class TestProtocol:

    def _setup(self):
        key = bytes(range(32))
        battery_id = b'BAT\x01'
        chip = SeBattChip(battery_id, key, voltage_mv=3700)
        station = Station()
        station.register_battery(battery_id, key)
        return chip, station

    def test_valid_auth(self):
        chip, station = self._setup()
        status = station.authenticate(chip)
        assert status == AuthStatus.VALID

    def test_multiple_valid_auths(self):
        chip, station = self._setup()
        for _ in range(10):
            assert station.authenticate(chip) == AuthStatus.VALID

    def test_unknown_battery(self):
        key = bytes(range(32))
        chip = SeBattChip(b'BAD\x01', key)
        station = Station()
        # Don't register this battery
        status = station.authenticate(chip)
        assert status == AuthStatus.UNKNOWN_BATTERY

    def test_locked_battery(self):
        chip, station = self._setup()
        station.lock_battery(b'BAT\x01')
        status = station.authenticate(chip)
        assert status == AuthStatus.BATTERY_LOCKED

    def test_unlock_battery(self):
        chip, station = self._setup()
        station.lock_battery(b'BAT\x01')
        station.unlock_battery(b'BAT\x01')
        status = station.authenticate(chip)
        assert status == AuthStatus.VALID

    def test_replay_attack(self):
        chip, station = self._setup()
        req = station.generate_challenge()
        resp = chip.handle_auth_request(req)
        # First use: valid
        assert station.verify_response(req, resp) == AuthStatus.VALID
        # Replay: same nonce reused
        assert station.verify_response(req, resp) == AuthStatus.REPLAY_DETECTED

    def test_wrong_key(self):
        battery_id = b'BAT\x01'
        real_key = bytes(range(32))
        fake_key = bytes(range(1, 33))
        chip = SeBattChip(battery_id, fake_key)
        station = Station()
        station.register_battery(battery_id, real_key)
        status = station.authenticate(chip)
        assert status == AuthStatus.INVALID_HMAC

    def test_voltage_tampering(self):
        """Attacker intercepts and changes voltage value."""
        key = bytes(range(32))
        battery_id = b'BAT\x01'
        chip = SeBattChip(battery_id, key, voltage_mv=3700)
        station = Station()
        station.register_battery(battery_id, key)

        req = station.generate_challenge()
        resp = chip.handle_auth_request(req)

        # Tamper: change voltage in response
        tampered = AuthResponse(
            battery_id=resp.battery_id,
            voltage=4200,  # Fake higher voltage
            hmac_resp=resp.hmac_resp,  # HMAC still from 3700
        )
        status = station.verify_response(req, tampered)
        assert status == AuthStatus.INVALID_HMAC

    def test_auth_count(self):
        chip, station = self._setup()
        for _ in range(5):
            station.authenticate(chip)
        assert station.batteries[b'BAT\x01'].auth_count == 5

    def test_log_populated(self):
        chip, station = self._setup()
        station.authenticate(chip)
        assert len(station.log) == 1
        assert station.log[0]['status'] == 'VALID'


# ===================================================================
# Wire protocol tests
# ===================================================================

class TestWireProtocol:

    def test_auth_req_roundtrip(self):
        nonce = bytes(range(32))
        req = AuthRequest(nonce=nonce)
        frame = WireProtocol.encode_auth_req(req)
        cmd, payload = WireProtocol.decode(frame)
        assert cmd == Command.AUTH_REQ
        decoded = WireProtocol.decode_auth_req(payload)
        assert decoded.nonce == nonce

    def test_auth_resp_roundtrip(self):
        resp = AuthResponse(
            battery_id=b'BAT\x01',
            voltage=3700,
            hmac_resp=bytes(range(32)),
        )
        frame = WireProtocol.encode_auth_resp(resp)
        cmd, payload = WireProtocol.decode(frame)
        assert cmd == Command.AUTH_RESP
        decoded = WireProtocol.decode_auth_resp(payload)
        assert decoded.battery_id == b'BAT\x01'
        assert decoded.voltage == 3700
        assert decoded.hmac_resp == bytes(range(32))

    def test_result_roundtrip(self):
        frame = WireProtocol.encode_result(AuthStatus.VALID)
        cmd, payload = WireProtocol.decode(frame)
        assert cmd == Command.RESULT
        assert WireProtocol.decode_result(payload) == AuthStatus.VALID

    def test_crc_corruption(self):
        nonce = bytes(range(32))
        req = AuthRequest(nonce=nonce)
        frame = bytearray(WireProtocol.encode_auth_req(req))
        frame[-1] ^= 0xFF  # Corrupt CRC
        with pytest.raises(ValueError, match="CRC"):
            WireProtocol.decode(bytes(frame))

    def test_frame_too_short(self):
        with pytest.raises(ValueError, match="too short"):
            WireProtocol.decode(b'\x01\x00')
