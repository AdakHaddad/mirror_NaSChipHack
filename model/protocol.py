"""
SeBatt challenge-response authentication protocol.

Models the full auth flow between station (verifier) and chip (prover):

  Station                          Chip (FPGA)
    │                                │
    │──── AUTH_REQ + nonce ──────────>│
    │                                │ read ADC voltage
    │                                │ msg = nonce || battery_id || voltage
    │                                │ resp = HMAC-SHA256(key, msg)
    │<─── AUTH_RESP + voltage + resp ─│
    │                                │
    │ recompute HMAC, compare        │
    │ check replay (nonce reuse)     │
    │ check lock status              │
    │──── RESULT (VALID/INVALID) ───>│
    │                                │

Protocol matches what RTL auth_ctrl FSM + C firmware will do.
"""

import os
import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

from .hmac import hmac_sha256
from .ro_puf import KeyVault, ROPUFModel, PUFInstance


class AuthStatus(IntEnum):
    VALID = 0x00
    INVALID_HMAC = 0x01
    REPLAY_DETECTED = 0x02
    BATTERY_LOCKED = 0x03
    UNKNOWN_BATTERY = 0x04


class Command(IntEnum):
    AUTH_REQ = 0x01
    AUTH_RESP = 0x02
    RESULT = 0x03
    LOCK = 0x04
    UNLOCK = 0x05
    STATUS = 0x06


@dataclass
class Battery:
    """One registered battery."""
    battery_id: bytes          # 4 bytes
    key: bytes                 # 32 bytes (from KeyVault or PUF enrollment)
    locked: bool = False
    auth_count: int = 0


@dataclass
class AuthRequest:
    """Station → Chip."""
    nonce: bytes               # 32 bytes random


@dataclass
class AuthResponse:
    """Chip → Station."""
    battery_id: bytes          # 4 bytes
    voltage: int               # 16-bit ADC reading (millivolts)
    hmac_resp: bytes           # 32 bytes


# ---------------------------------------------------------------------------
# Chip side (runs on FPGA / MicroBlaze)
# ---------------------------------------------------------------------------

class SeBattChip:
    """
    Models the chip/FPGA side of authentication.
    In real HW: auth_ctrl FSM + HMAC IP + key_vault/ro_puf.
    """

    def __init__(self, battery_id: bytes, key: bytes,
                 voltage_mv: int = 3700):
        assert len(battery_id) == 4
        assert len(key) == 32
        self.battery_id = battery_id
        self.key = key
        self.voltage_mv = voltage_mv  # Simulated ADC reading

    def set_voltage(self, mv: int):
        """Simulate ADC reading change."""
        self.voltage_mv = mv

    def handle_auth_request(self, request: AuthRequest) -> AuthResponse:
        """
        Process authentication challenge:
          1. Read voltage (ADC)
          2. Build message = nonce || battery_id || voltage
          3. Compute HMAC-SHA-256(key, message)
          4. Return response
        """
        voltage_bytes = struct.pack('>H', self.voltage_mv)
        message = request.nonce + self.battery_id + voltage_bytes
        resp = hmac_sha256(self.key, message)
        return AuthResponse(
            battery_id=self.battery_id,
            voltage=self.voltage_mv,
            hmac_resp=resp,
        )


# ---------------------------------------------------------------------------
# Station side (runs on PC / Python)
# ---------------------------------------------------------------------------

class Station:
    """
    Models the station + identity database.
    Verifies battery authenticity, detects replay and tampering.
    """

    def __init__(self):
        self.batteries: dict[bytes, Battery] = {}
        self.used_nonces: set[bytes] = set()
        self.log: list[dict] = []

    def register_battery(self, battery_id: bytes, key: bytes):
        """Enroll battery in identity database."""
        self.batteries[battery_id] = Battery(
            battery_id=battery_id,
            key=key,
        )

    def lock_battery(self, battery_id: bytes):
        """Lock battery (e.g., stolen, recalled, end-of-life)."""
        if battery_id in self.batteries:
            self.batteries[battery_id].locked = True

    def unlock_battery(self, battery_id: bytes):
        """Unlock battery."""
        if battery_id in self.batteries:
            self.batteries[battery_id].locked = False

    def generate_challenge(self) -> AuthRequest:
        """Generate random nonce for authentication challenge."""
        nonce = os.urandom(32)
        return AuthRequest(nonce=nonce)

    def verify_response(self, request: AuthRequest,
                        response: AuthResponse) -> AuthStatus:
        """
        Verify chip's authentication response:
          1. Check battery is registered
          2. Check battery not locked
          3. Check nonce not reused (replay detection)
          4. Recompute HMAC and compare
        """
        bid = response.battery_id

        # Unknown battery
        if bid not in self.batteries:
            self._log(bid, AuthStatus.UNKNOWN_BATTERY, request.nonce)
            return AuthStatus.UNKNOWN_BATTERY

        battery = self.batteries[bid]

        # Locked battery
        if battery.locked:
            self._log(bid, AuthStatus.BATTERY_LOCKED, request.nonce)
            return AuthStatus.BATTERY_LOCKED

        # Replay detection
        if request.nonce in self.used_nonces:
            self._log(bid, AuthStatus.REPLAY_DETECTED, request.nonce)
            return AuthStatus.REPLAY_DETECTED
        self.used_nonces.add(request.nonce)

        # Recompute HMAC
        voltage_bytes = struct.pack('>H', response.voltage)
        message = request.nonce + bid + voltage_bytes
        expected = hmac_sha256(battery.key, message)

        if response.hmac_resp != expected:
            self._log(bid, AuthStatus.INVALID_HMAC, request.nonce)
            return AuthStatus.INVALID_HMAC

        battery.auth_count += 1
        self._log(bid, AuthStatus.VALID, request.nonce)
        return AuthStatus.VALID

    def _log(self, battery_id: bytes, status: AuthStatus, nonce: bytes):
        self.log.append({
            'battery_id': battery_id.hex(),
            'status': status.name,
            'nonce': nonce[:8].hex() + '...',
            'time': time.time(),
        })

    def authenticate(self, chip: SeBattChip) -> AuthStatus:
        """Full auth flow: generate challenge → get response → verify."""
        req = self.generate_challenge()
        resp = chip.handle_auth_request(req)
        return self.verify_response(req, resp)


# ---------------------------------------------------------------------------
# Wire protocol (maps to UART frames in firmware)
# ---------------------------------------------------------------------------

class WireProtocol:
    """
    Packet format for UART communication.
    Simple framing for PoC — not production quality.

    Frame: [CMD:1][LEN:2][PAYLOAD:LEN][CRC8:1]

    AUTH_REQ  payload: nonce (32 bytes)
    AUTH_RESP payload: battery_id (4) + voltage (2) + hmac (32) = 38 bytes
    RESULT    payload: status (1 byte)
    """

    @staticmethod
    def encode_auth_req(request: AuthRequest) -> bytes:
        payload = request.nonce
        return WireProtocol._frame(Command.AUTH_REQ, payload)

    @staticmethod
    def encode_auth_resp(response: AuthResponse) -> bytes:
        payload = (response.battery_id
                   + struct.pack('>H', response.voltage)
                   + response.hmac_resp)
        return WireProtocol._frame(Command.AUTH_RESP, payload)

    @staticmethod
    def encode_result(status: AuthStatus) -> bytes:
        return WireProtocol._frame(Command.RESULT, bytes([status]))

    @staticmethod
    def decode(frame: bytes) -> tuple:
        """Returns (Command, payload_bytes)."""
        if len(frame) < 4:
            raise ValueError("Frame too short")
        cmd = Command(frame[0])
        length = struct.unpack('>H', frame[1:3])[0]
        payload = frame[3:3 + length]
        crc = frame[3 + length]
        if crc != WireProtocol._crc8(frame[:3 + length]):
            raise ValueError("CRC mismatch")
        return cmd, payload

    @staticmethod
    def decode_auth_req(payload: bytes) -> AuthRequest:
        return AuthRequest(nonce=payload[:32])

    @staticmethod
    def decode_auth_resp(payload: bytes) -> AuthResponse:
        return AuthResponse(
            battery_id=payload[:4],
            voltage=struct.unpack('>H', payload[4:6])[0],
            hmac_resp=payload[6:38],
        )

    @staticmethod
    def decode_result(payload: bytes) -> AuthStatus:
        return AuthStatus(payload[0])

    @staticmethod
    def _frame(cmd: Command, payload: bytes) -> bytes:
        header = bytes([cmd]) + struct.pack('>H', len(payload))
        data = header + payload
        return data + bytes([WireProtocol._crc8(data)])

    @staticmethod
    def _crc8(data: bytes) -> int:
        """CRC-8/MAXIM for error detection. Simple, maps to small LUT in RTL."""
        crc = 0x00
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ 0x31) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
        return crc
