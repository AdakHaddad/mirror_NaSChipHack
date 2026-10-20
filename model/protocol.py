"""
SeBatt challenge-response authentication and history protocol.

Models the full flow between station (verifier) and chip (prover):

  Station                                    Chip (FPGA)
    |                                            |
    |---- AUTH_REQ + nonce --------------------->| periodic sampling
    |                                            | msg = 0x41|nonce|ID|V
    |<--- AUTH_RESP + voltage + tag (0x41) ------| tag = HMAC(key, msg)
    |                                            |
    | recompute tag, compare                     |
    | check replay (nonce reuse)                 |
    |---- RESULT (VALID/INVALID) ---------------->| fail counter, lock at 3
    |                                            |
    |---- READ_HIST_REQ + nonce (0x07) ---------->| per-record 0x53 tags, stored
    |<--- READ_HIST_RESP dump + 0x48 summary ----| summary binds nonce->range
    |                                            |

Wire format (spec section 7): [CMD:1][LEN:2 BE][PAYLOAD:LEN][CRC8:1]

Signed message prefixes (spec section 6):
  0x41 AUTH     nonce(32) || battery_id(4) || voltage(2)     = 39 bytes
  0x53 RECORD   battery_id(4) || seq(4) || voltage(2)        = 11 bytes
  0x48 SUMMARY  nonce(32) || battery_id(4) ||
                seq_oldest(4) || seq_last(4)                 = 45 bytes
"""

import os
import struct
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

from .hmac import hmac_sha256
from .ro_puf import KeyVault, ROPUFModel, PUFInstance

AUTH_MSG_PREFIX = 0x41
RECORD_MSG_PREFIX = 0x53
SUMMARY_MSG_PREFIX = 0x48


class AuthStatus(IntEnum):
    VALID = 0x00
    INVALID_HMAC = 0x01
    REPLAY_DETECTED = 0x02
    BATTERY_LOCKED = 0x03
    UNKNOWN_BATTERY = 0x04
    HISTORY_GAP = 0x05
    HISTORY_ROLLBACK = 0x06
    HISTORY_TRUNCATED = 0x07


class Command(IntEnum):
    AUTH_REQ = 0x01
    AUTH_RESP = 0x02
    RESULT = 0x03
    LOCK = 0x04
    UNLOCK = 0x05
    STATUS = 0x06
    READ_HIST_REQ = 0x07
    READ_HIST_RESP = 0x08
    CHIP_LOCKED = 0x09


# RESULT statuses that reset the chip fail counter (spec section 11)
ACCEPTING_STATUSES = (AuthStatus.VALID, AuthStatus.HISTORY_TRUNCATED)


@dataclass
class Battery:
    """One registered battery."""
    battery_id: bytes          # 4 bytes
    key: bytes                 # 32 bytes (from KeyVault or PUF enrollment)
    locked: bool = False
    auth_count: int = 0
    seq_anchor: int = 0        # last verified seq in the database


@dataclass
class AuthRequest:
    """Station -> Chip."""
    nonce: bytes               # 32 bytes random


@dataclass
class AuthResponse:
    """Chip -> Station."""
    battery_id: bytes          # 4 bytes
    voltage: int               # 16-bit ADC reading (millivolts)
    hmac_resp: bytes           # 32 bytes


@dataclass
class HistoryRecord:
    """One signed sample inside the chip history buffer."""
    seq: int
    mv: int
    tag: bytes


@dataclass
class HistoryDump:
    """Chip -> Station, READ_HIST_RESP payload (spec section 8)."""
    battery_id: bytes          # 4 bytes
    seq_oldest: int
    seq_last: int
    records: list              # list of HistoryRecord
    summary_tag: bytes         # 32 bytes

    def encode(self) -> bytes:
        payload = struct.pack('B', len(self.records))
        payload += struct.pack('>II', self.seq_oldest, self.seq_last)
        for rec in self.records:
            payload += (struct.pack('>IH', rec.seq, rec.mv) + rec.tag)
        payload += self.summary_tag
        return payload


# ---------------------------------------------------------------------------
# Chip side (runs on FPGA / MicroBlaze)
# ---------------------------------------------------------------------------

class SeBattChip:
    """
    Models the chip/FPGA side: authentication plus the signed history
    buffer with the lock behavior of spec section 11.
    In real HW: auth_ctrl FSM + HMAC IP + key_vault/ro_puf.
    """

    def __init__(self, battery_id: bytes, key: bytes,
                 voltage_mv: int = 3700, buffer_size: int = 64):
        assert len(battery_id) == 4
        assert len(key) == 32
        self.battery_id = battery_id
        self.key = key
        self.voltage_mv = voltage_mv  # Simulated ADC reading
        self.buffer_size = buffer_size
        self.records: list[HistoryRecord] = []
        self.next_seq = 0             # seq assigned to the next sample
        self.locked = False
        self.fail_count = 0

    def set_voltage(self, mv: int):
        """Simulate one periodic sample."""
        self.voltage_mv = mv

    def sample_tick(self):
        """One periodic sample: store a signed record (0x53 message)."""
        seq = self.next_seq
        self.next_seq += 1
        message = (bytes([RECORD_MSG_PREFIX]) + self.battery_id
                   + struct.pack('>IH', seq, self.voltage_mv))
        rec = HistoryRecord(seq=seq, mv=self.voltage_mv,
                            tag=hmac_sha256(self.key, message))
        self.records.append(rec)
        if len(self.records) > self.buffer_size:
            self.records.pop(0)

    def history_snapshot(self) -> tuple:
        """(records, seq_oldest, seq_last) currently in the chip buffer.

        Seq numbers are unsigned 32-bit and wrap; an empty buffer reports
        seq_last = seq_oldest - 1 (N = 0 modulo 2**32), matching the RTL.
        """
        seq_last = (self.next_seq - 1) & 0xFFFFFFFF
        n = min(len(self.records), self.buffer_size)
        seq_oldest = (seq_last - n + 1) & 0xFFFFFFFF
        return self.records, seq_oldest, seq_last

    def handle_auth_request(self, request: AuthRequest):
        """
        Process authentication challenge, or CHIP_LOCKED when locked.
        Message: 0x41 || nonce || battery_id || voltage.
        """
        if self.locked:
            return None
        voltage_bytes = struct.pack('>H', self.voltage_mv)
        message = (bytes([AUTH_MSG_PREFIX]) + request.nonce
                   + self.battery_id + voltage_bytes)
        resp = hmac_sha256(self.key, message)
        return AuthResponse(
            battery_id=self.battery_id,
            voltage=self.voltage_mv,
            hmac_resp=resp,
        )

    def chip_locked(self) -> bytes:
        """CHIP_LOCKED payload: battery ID (4 bytes)."""
        return self.battery_id

    def handle_read_hist_request(self, nonce: bytes):
        """
        Dump the history buffer. Summary message (0x48):
        nonce(32) || battery_id(4) || seq_oldest(4) || seq_last(4).
        """
        if self.locked:
            return None
        records, seq_oldest, seq_last = self.history_snapshot()
        summary = (bytes([SUMMARY_MSG_PREFIX]) + nonce + self.battery_id
                   + struct.pack('>II', seq_oldest, seq_last))
        return HistoryDump(
            battery_id=self.battery_id,
            seq_oldest=seq_oldest,
            seq_last=seq_last,
            records=list(records),
            summary_tag=hmac_sha256(self.key, summary),
        )

    def handle_result(self, status: AuthStatus):
        """RESULT: reset the fail counter on acceptance, else bump/lock."""
        if status in ACCEPTING_STATUSES:
            self.fail_count = 0
        else:
            self.fail_count += 1
            if self.fail_count >= 3:
                self.locked = True

    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False
        self.fail_count = 0


# ---------------------------------------------------------------------------
# Station side (runs on PC / Python)
# ---------------------------------------------------------------------------

class Station:
    """
    Models the station + identity database.
    Verifies battery authenticity, history integrity, replay and tampering.
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

        # Recompute HMAC (0x41-prefixed message)
        voltage_bytes = struct.pack('>H', response.voltage)
        message = (bytes([AUTH_MSG_PREFIX]) + request.nonce + bid
                   + voltage_bytes)
        expected = hmac_sha256(battery.key, message)

        if response.hmac_resp != expected:
            self._log(bid, AuthStatus.INVALID_HMAC, request.nonce)
            return AuthStatus.INVALID_HMAC

        battery.auth_count += 1
        self._log(bid, AuthStatus.VALID, request.nonce)
        return AuthStatus.VALID

    def verify_history(self, request, battery_id: bytes,
                       dump: HistoryDump) -> AuthStatus:
        """
        Verify a READ_HIST_RESP (spec section 10):
          1. battery registered / not locked
          2. recompute summary tag with the fresh nonce (replay)
          3. HISTORY_ROLLBACK: seq_last below the database anchor
          4. HISTORY_GAP: records not contiguous N..seq_last
          5. recompute every record tag
          6. HISTORY_TRUNCATED: seq_oldest left a gap behind the anchor
          7. VALID: anchor moves to seq_last
        """
        if battery_id not in self.batteries:
            return AuthStatus.UNKNOWN_BATTERY
        battery = self.batteries[battery_id]
        if battery.locked:
            return AuthStatus.BATTERY_LOCKED

        nonce = request.nonce
        if nonce in self.used_nonces:
            self._log(battery_id, AuthStatus.REPLAY_DETECTED, nonce)
            return AuthStatus.REPLAY_DETECTED
        self.used_nonces.add(nonce)

        seq_oldest = int(dump.seq_oldest)
        seq_last = int(dump.seq_last)

        summary = (bytes([SUMMARY_MSG_PREFIX]) + nonce + battery_id
                   + struct.pack('>II', seq_oldest, seq_last))
        if dump.summary_tag != hmac_sha256(battery.key, summary):
            self._log(battery_id, AuthStatus.INVALID_HMAC, nonce)
            return AuthStatus.INVALID_HMAC

        n_records = len(dump.records)
        if n_records == 0:
            if seq_last != ((seq_oldest - 1) & 0xFFFFFFFF):
                self._log(battery_id, AuthStatus.HISTORY_GAP, nonce)
                return AuthStatus.HISTORY_GAP
            if battery.seq_anchor != 0:
                self._log(battery_id, AuthStatus.HISTORY_ROLLBACK, nonce)
                return AuthStatus.HISTORY_ROLLBACK
            self._log(battery_id, AuthStatus.VALID, nonce)
            return AuthStatus.VALID

        if seq_last < battery.seq_anchor:
            self._log(battery_id, AuthStatus.HISTORY_ROLLBACK, nonce)
            return AuthStatus.HISTORY_ROLLBACK

        seqs = [int(r.seq) & 0xFFFFFFFF for r in dump.records]
        n = len(seqs)
        expected = [(seq_oldest + i) & 0xFFFFFFFF for i in range(n)]
        if n != (seq_last - seq_oldest + 1) & 0xFFFFFFFF or seqs != expected:
            self._log(battery_id, AuthStatus.HISTORY_GAP, nonce)
            return AuthStatus.HISTORY_GAP

        for rec in dump.records:
            message = (bytes([RECORD_MSG_PREFIX]) + battery_id
                       + struct.pack('>IH', rec.seq, rec.mv))
            if rec.tag != hmac_sha256(battery.key, message):
                self._log(battery_id, AuthStatus.INVALID_HMAC, nonce)
                return AuthStatus.INVALID_HMAC

        truncated = seq_oldest > battery.seq_anchor + 1
        battery.seq_anchor = seq_last
        status = (AuthStatus.HISTORY_TRUNCATED if truncated
                  else AuthStatus.VALID)
        self._log(battery_id, status, nonce)
        return status

    def _log(self, battery_id: bytes, status: AuthStatus, nonce: bytes):
        self.log.append({
            'battery_id': battery_id.hex(),
            'status': status.name,
            'nonce': nonce[:8].hex() + '...',
            'time': time.time(),
        })

    def authenticate(self, chip: SeBattChip) -> AuthStatus:
        """Full auth flow: generate challenge -> get response -> verify."""
        req = self.generate_challenge()
        resp = chip.handle_auth_request(req)
        if resp is None:
            return AuthStatus.BATTERY_LOCKED
        return self.verify_response(req, resp)

    def read_history(self, chip: SeBattChip, battery_id: bytes,
                     nonce: Optional[bytes] = None):
        """Read and verify one history dump from the chip model."""
        if nonce is None:
            nonce = os.urandom(32)
        dump = chip.handle_read_hist_request(nonce)
        if dump is None:
            return AuthStatus.BATTERY_LOCKED, None
        request = AuthRequest(nonce=nonce)
        return self.verify_history(request, battery_id, dump), dump


# ---------------------------------------------------------------------------
# Wire protocol (maps to UART frames in firmware)
# ---------------------------------------------------------------------------

class WireProtocol:
    """
    Packet format for UART communication (spec section 7).

    AUTH_REQ  payload: nonce (32 bytes)
    AUTH_RESP payload: battery_id (4) + voltage (2) + hmac (32) = 38 bytes
    RESULT    payload: status (1 byte)
    READ_HIST_REQ payload: nonce (32 bytes)
    READ_HIST_RESP payload: HistoryDump.encode()
    CHIP_LOCKED payload: battery_id (4 bytes)
    """

    @staticmethod
    def encode_auth_req(request) -> bytes:
        """Accepts a 32-byte nonce or an AuthRequest."""
        nonce = request if isinstance(request, (bytes, bytearray)) \
            else request.nonce
        return WireProtocol._frame(Command.AUTH_REQ, bytes(nonce))

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
    def encode_read_hist_req(nonce: bytes) -> bytes:
        return WireProtocol._frame(Command.READ_HIST_REQ, nonce)

    @staticmethod
    def encode_read_hist_resp(dump: HistoryDump) -> bytes:
        return WireProtocol._frame(Command.READ_HIST_RESP, dump.encode())

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
    def decode_history(payload: bytes) -> HistoryDump:
        n = payload[0]
        seq_oldest, seq_last = struct.unpack('>II', payload[1:9])
        records = []
        off = 9
        for _ in range(n):
            seq, mv = struct.unpack('>IH', payload[off:off + 6])
            tag = payload[off + 6:off + 38]
            records.append(HistoryRecord(seq=seq, mv=mv, tag=tag))
            off += 38
        summary_tag = payload[off:off + 32]
        return HistoryDump(
            battery_id=b'',
            seq_oldest=seq_oldest,
            seq_last=seq_last,
            records=records,
            summary_tag=summary_tag,
        )

    @staticmethod
    def _frame(cmd, payload: bytes) -> bytes:
        header = bytes([cmd]) + struct.pack('>H', len(payload))
        data = header + payload
        return data + bytes([WireProtocol._crc8(data)])

    @staticmethod
    def _crc8(data: bytes) -> int:
        """CRC-8 for error detection. Simple, maps to small LUT in RTL."""
        crc = 0x00
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ 0x31) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
        return crc
