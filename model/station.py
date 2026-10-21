#!/usr/bin/env python3
"""
SeBatt station emulator — PC side of the PoC demo.
Talks to FPGA board via UART, sends auth challenges, verifies responses.

Usage:
    python -m model.station                          # auto-detect port
    python -m model.station --port /dev/ttyUSB1      # explicit port
    python -m model.station --demo                   # run demo sequence
    python -m model.station --benchmark              # throughput test

Requires: pyserial
    pip install pyserial
"""

import argparse
import os
import struct
import sys
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

# Use our own HMAC implementation for verification
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from model.hmac import hmac_sha256
from model.protocol import (
    AuthStatus, Command, WireProtocol,
    AuthRequest, AuthResponse, HistoryDump, HistoryRecord,
    AUTH_MSG_PREFIX, RECORD_MSG_PREFIX, SUMMARY_MSG_PREFIX,
)


# -----------------------------------------------------------------------
# Verdict wording for the demo screen
# -----------------------------------------------------------------------
ACCEPTED = (AuthStatus.VALID, AuthStatus.HISTORY_TRUNCATED)

STATUS_NOTES = {
    AuthStatus.HISTORY_TRUNCATED:
        "Diterima. Catatan lebih lama dari jangkar stasiun sudah tertimpa di "
        "buffer 64 catatan (wajar pada dump pertama setelah stasiun dijalankan).",
    AuthStatus.HISTORY_ROLLBACK:
        "Nomor urut chip lebih kecil dari catatan stasiun. Chip direset atau "
        "dimuat ulang. Kalau disengaja, jalankan reset-anchor.",
    AuthStatus.HISTORY_GAP:
        "Ada nomor urut yang hilang: catatan dibuang di tengah jalan.",
    AuthStatus.INVALID_HMAC:
        "Tanda tangan tidak cocok: data diubah, rentang dipalsukan, atau "
        "jawaban lama diputar ulang.",
    AuthStatus.BATTERY_LOCKED:
        "Chip terkunci. Ketik unlock untuk membuka.",
}


def verdict(status: AuthStatus) -> str:
    return "DITERIMA" if status in ACCEPTED else "DITOLAK"


# Battery profiles. The chip signs the millivolts at the ADC pin; the station
# converts them to battery millivolts with `scale` and judges health there.
# One set of rules for the CLI and the dashboard.
PROFILES = {
    # Knob straight on A0 standing in for one Li-ion cell: 0-3.3 V at the pin
    # is read as 0-4.2 V. Deep discharge below 2.5 V; a charge cycle is a dip
    # below 3.0 V followed by a rise above 4.0 V.
    "sel": {
        "name": "sel",
        "label": "sel Li-ion (kenop 0-3,3 V di A0 dibaca 0-4,2 V)",
        "scale": 4200 / 3300,
        "deep_mv": 2500,
        "arm_mv": 3000,
        "full_mv": 4000,
    },
    # 12 V lead-acid battery behind the 47k/10k divider in the casing.
    "aki12v": {
        "name": "aki12v",
        "label": "aki 12 V lewat pembagi 47k/10k (pin × 5,7)",
        "scale": 5.7,
        "deep_mv": 10500,
        "arm_mv": 11800,
        "full_mv": 12600,
    },
}
DEFAULT_PROFILE = "sel"


def to_battery_mv(pin_mv: int, profile: dict) -> int:
    return int(round(pin_mv * profile["scale"]))


def to_pin_mv(battery_mv: int, profile: dict) -> int:
    return int(round(battery_mv / profile["scale"]))


def health_summary(records, profile: dict) -> Optional[dict]:
    """Battery health from an already verified history (station side only).

    All values are battery millivolts. A run of consecutive samples below
    deep_mv counts as one deep-discharge event.
    """
    if not records:
        return None
    pts = [(r.seq, to_battery_mv(r.mv, profile)) for r in sorted(records, key=lambda r: r.seq)]
    events, below, cycles, armed = 0, False, 0, False
    for _, mv in pts:
        if mv < profile["deep_mv"] and not below:
            events += 1
        below = mv < profile["deep_mv"]
        if mv < profile["arm_mv"]:
            armed = True
        elif mv > profile["full_mv"] and armed:
            cycles += 1
            armed = False
    low_seq, low_mv = min(pts, key=lambda p: p[1])
    return {
        "min_mv": low_mv,
        "min_seq": low_seq,
        "max_mv": max(mv for _, mv in pts),
        "last_mv": pts[-1][1],
        "deep_events": events,
        "cycles": cycles,
        "samples": len(pts),
    }


def health_card(records, profile: dict) -> list:
    """Health summary as text lines for the CLI."""
    h = health_summary(records, profile)
    if h is None:
        return ["Kesehatan: belum ada catatan"]

    def v(mv):
        return f"{mv / 1000:.2f} V".replace(".", ",")

    lines = [f"Kesehatan ({profile['label']}): terendah {v(h['min_mv'])} pada seq "
             f"{h['min_seq']}, terbaru {v(h['last_mv'])}, siklus {h['cycles']}"]
    if h["deep_events"]:
        lines.append(f"PERHATIAN: terkuras dalam {h['deep_events']} kali "
                     f"(di bawah {v(profile['deep_mv'])}). Riwayat asli, baterai perlu diperiksa.")
    else:
        lines.append(f"Tidak ada kejadian di bawah {v(profile['deep_mv'])}.")
    return lines


# -----------------------------------------------------------------------
# Identity database
# -----------------------------------------------------------------------
@dataclass
class BatteryRecord:
    battery_id: bytes
    key: bytes
    locked: bool = False
    auth_count: int = 0
    seq_anchor: int = 0


class IdentityDB:
    """In-memory battery identity database."""

    def __init__(self):
        self.batteries: dict[bytes, BatteryRecord] = {}
        self.used_nonces: set[bytes] = set()

    def register(self, battery_id: bytes, key: bytes):
        self.batteries[battery_id] = BatteryRecord(battery_id=battery_id, key=key)

    def lookup(self, battery_id: bytes) -> Optional[BatteryRecord]:
        return self.batteries.get(battery_id)

    def is_nonce_used(self, nonce: bytes) -> bool:
        return nonce in self.used_nonces

    def mark_nonce_used(self, nonce: bytes):
        self.used_nonces.add(nonce)


# -----------------------------------------------------------------------
# Station
# -----------------------------------------------------------------------
class Station:
    """Station emulator that communicates with SeBatt chip via UART."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 2.0):
        if serial is None:
            raise ImportError("pyserial required: pip install pyserial")
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.db = IdentityDB()
        self.log = []
        self.last_battery_id: Optional[bytes] = None
        # Tell the chip each verdict (RESULT) so its fail counter and lock
        # follow the station, as in spec sections 10 and 11.
        self.report_results = True
        # Battery profile for the health card (see PROFILES).
        self.profile = PROFILES[DEFAULT_PROFILE]
        # (seq_last, time first seen) to notice a sensor that stopped sampling
        self._last_seen: Optional[tuple] = None

        # Register default battery (matches firmware)
        default_key = bytes(range(32))
        self.db.register(b'BAT\x01', default_key)

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    # --- Low-level UART I/O ---

    def _send_frame(self, cmd: int, payload: bytes):
        """Send wire protocol frame."""
        # Drop stale bytes (adapter plug-in noise, a late reply) so the next
        # read starts at a frame boundary.
        self.ser.reset_input_buffer()
        header = bytes([cmd]) + struct.pack('>H', len(payload))
        data = header + payload
        crc = self._crc8(data)
        self.ser.write(data + bytes([crc]))
        self.ser.flush()

    def _recv_frame(self, timeout: float = 2.0) -> tuple:
        """Receive wire protocol frame. Returns (cmd, payload)."""
        old_timeout = self.ser.timeout
        self.ser.timeout = timeout

        try:
            header = self.ser.read(3)
            if len(header) < 3:
                raise TimeoutError("No response from chip")

            cmd = header[0]
            length = struct.unpack('>H', header[1:3])[0]
            payload = self.ser.read(length)
            if len(payload) < length:
                raise TimeoutError("Incomplete payload")

            crc_byte = self.ser.read(1)
            if len(crc_byte) < 1:
                raise TimeoutError("Missing CRC")

            expected_crc = self._crc8(header + payload)
            if crc_byte[0] != expected_crc:
                raise ValueError(f"CRC mismatch: got {crc_byte[0]:02X}, expected {expected_crc:02X}")

            return cmd, payload
        finally:
            self.ser.timeout = old_timeout

    @staticmethod
    def _crc8(data: bytes) -> int:
        crc = 0x00
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ 0x31) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
        return crc

    # --- Auth protocol ---

    def authenticate(self, report: bool = True) -> tuple:
        """
        Run full authentication:
          1. Generate random nonce
          2. Send AUTH_REQ to chip
          3. Receive AUTH_RESP
          4. Verify HMAC

        Returns: (AuthStatus, voltage, battery_id_hex)
        Set ``report=False`` when the caller will send one RESULT for the
        whole transaction (for example auth followed by history verification).
        """
        # Generate nonce
        nonce = os.urandom(32)

        # Send AUTH_REQ
        self._send_frame(Command.AUTH_REQ, nonce)

        # Receive AUTH_RESP
        cmd, payload = self._recv_frame()
        if cmd == Command.CHIP_LOCKED:
            payload_id = payload[0:4]
            self.log.append({
                'status': AuthStatus.BATTERY_LOCKED.name,
                'battery_id': payload_id.hex(),
                'voltage': 0,
                'time': time.time(),
            })
            return AuthStatus.BATTERY_LOCKED, 0, payload_id.hex()

        if cmd != Command.AUTH_RESP:
            return AuthStatus.INVALID_HMAC, 0, ""

        if len(payload) < 38:
            return AuthStatus.INVALID_HMAC, 0, ""

        # Parse response
        battery_id = payload[0:4]
        voltage = struct.unpack('>H', payload[4:6])[0]
        hmac_resp = payload[6:38]

        # Verify
        record = self.db.lookup(battery_id)
        if record is None:
            status = AuthStatus.UNKNOWN_BATTERY
        elif record.locked:
            status = AuthStatus.BATTERY_LOCKED
        elif self.db.is_nonce_used(nonce):
            status = AuthStatus.REPLAY_DETECTED
        else:
            self.db.mark_nonce_used(nonce)
            # Recompute HMAC
            msg = (bytes([AUTH_MSG_PREFIX]) + nonce + battery_id
                   + struct.pack('>H', voltage))
            expected = hmac_sha256(record.key, msg)
            if hmac_resp == expected:
                status = AuthStatus.VALID
                record.auth_count += 1
            else:
                status = AuthStatus.INVALID_HMAC

        self.last_battery_id = battery_id
        self.log.append({
            'status': status.name,
            'battery_id': battery_id.hex(),
            'voltage': voltage,
            'time': time.time(),
        })
        if report:
            self.report_result(status)

        return status, voltage, battery_id.hex()

    def read_history_raw(self, battery_id: Optional[bytes] = None,
                         nonce: Optional[bytes] = None):
        """Request a history dump without verifying it.

        Returns ``(transport_status, nonce, dump)``. A non-VALID transport
        status means the chip did not return a usable dump; the caller can
        still use ``verify_history`` later with the same nonce. This is what
        the dashboard uses to show live samples before the user verifies.
        """
        if battery_id is None:
            battery_id = self.last_battery_id
        if battery_id is None:
            raise ValueError("battery_id required before reading history")
        if nonce is None:
            nonce = os.urandom(32)

        self._send_frame(Command.READ_HIST_REQ, nonce)
        cmd, payload = self._recv_frame()

        if cmd == Command.CHIP_LOCKED:
            return AuthStatus.BATTERY_LOCKED, nonce, None
        if cmd != Command.READ_HIST_RESP:
            return AuthStatus.INVALID_HMAC, nonce, None

        dump = WireProtocol.decode_history(payload)
        dump.battery_id = battery_id
        return AuthStatus.VALID, nonce, dump

    def read_history(self, battery_id: Optional[bytes] = None,
                     nonce: Optional[bytes] = None):
        """Request and verify a signed history dump."""
        transport, nonce, dump = self.read_history_raw(battery_id, nonce)
        if dump is None:
            return transport, None
        status = self.verify_history(dump.battery_id, nonce, dump)
        self.report_result(status)
        return status, dump

    def report_result(self, status: AuthStatus):
        """Send RESULT so the chip's fail counter tracks the verdict."""
        if self.report_results:
            self._send_frame(Command.RESULT, bytes([int(status)]))

    def query_status(self) -> tuple:
        """STATUS -> (locked, fail_cnt) as reported by the chip."""
        self._send_frame(Command.STATUS, b'')
        cmd, payload = self._recv_frame()
        if cmd != Command.STATUS or len(payload) < 2:
            raise ValueError(f"unexpected STATUS reply: cmd {cmd:#04x}")
        return bool(payload[0]), payload[1]

    def read_history_attacked(self, battery_id: bytes, mode: str,
                              seq: Optional[int] = None,
                              count: int = 3, mv: int = 3600):
        """Play the dishonest BMS: fetch a real dump from the chip, alter it
        after it left the chip, then verify it like the station would.

        mode: 'tamper' (change one voltage), 'delete' (drop records in the
        middle), 'cut' (drop the newest records and shrink the range),
        'replay' (answer a new nonce with a dump signed for an old one).
        For 'tamper', mv is the forged battery voltage in the station's
        profile (default 3.6 V); it is converted back to ADC-pin millivolts.
        Returns (status, description).
        """
        nonce = os.urandom(32)
        self._send_frame(Command.READ_HIST_REQ, nonce)
        cmd, payload = self._recv_frame()
        if cmd == Command.CHIP_LOCKED:
            return AuthStatus.BATTERY_LOCKED, "chip terkunci"
        if cmd != Command.READ_HIST_RESP:
            return AuthStatus.INVALID_HMAC, f"balasan tak terduga {cmd:#04x}"
        dump = WireProtocol.decode_history(payload)
        dump.battery_id = battery_id
        recs = dump.records
        if len(recs) < 4:
            return None, "riwayat terlalu pendek, tunggu beberapa detik"

        idx = len(recs) // 2
        if seq is not None:
            idx = next((i for i, r in enumerate(recs) if r.seq == seq), idx)

        if mode == 'tamper':
            old = recs[idx]
            forged = to_pin_mv(mv, self.profile)
            recs[idx] = HistoryRecord(seq=old.seq, mv=forged, tag=old.tag)
            old_v = to_battery_mv(old.mv, self.profile) / 1000
            desc = (f"seq {old.seq}: {old_v:.2f} V diubah menjadi {mv / 1000:.2f} V "
                    f"(pin {old.mv} -> {forged} mV)").replace(".", ",")
        elif mode == 'delete':
            count = max(1, min(count, len(recs) - 2))
            idx = max(1, min(idx, len(recs) - count - 1))
            gone = [r.seq for r in recs[idx:idx + count]]
            del recs[idx:idx + count]
            desc = f"seq {gone[0]}..{gone[-1]} dibuang dari tengah"
        elif mode == 'cut':
            count = max(1, min(count, len(recs) - 1))
            del recs[len(recs) - count:]
            dump.seq_last = recs[-1].seq
            desc = f"{count} catatan terbaru dibuang, rentang dipalsukan"
        elif mode == 'replay':
            nonce = os.urandom(32)
            desc = "dump untuk nonce lama dikirim sebagai jawaban nonce baru"
        else:
            raise ValueError(f"unknown attack mode: {mode}")

        status = self.verify_history(battery_id, nonce, dump)
        self.report_result(status)
        return status, desc

    def history_report(self, status: AuthStatus,
                       dump: Optional[HistoryDump]) -> list:
        """Human-readable lines for a verified (or rejected) history: the
        verdict, what it means, a health card for accepted histories, and a
        warning when the chip has stopped producing new samples."""
        lines = []
        if dump is None:
            lines.append(f"History: {status.name} -> {verdict(status)}")
            note = STATUS_NOTES.get(status)
            if note:
                lines.append(f"  {note}")
            return lines

        lines.append(f"History: {len(dump.records)} catatan, seq "
                     f"{dump.seq_oldest}..{dump.seq_last} -> {status.name} "
                     f"({verdict(status)})")
        note = STATUS_NOTES.get(status)
        if note:
            lines.append(f"  {note}")
        if status not in ACCEPTED:
            lines.append("  Riwayat: TIDAK DAPAT DIPERCAYA, kartu kesehatan tidak ditampilkan")
            return lines

        lines.extend("  " + l for l in health_card(dump.records, self.profile))

        now = time.monotonic()
        if self._last_seen and self._last_seen[0] == dump.seq_last:
            idle = now - self._last_seen[1]
            if idle >= 3.0:
                lines.append(f"  PERINGATAN: tidak ada catatan baru selama {idle:.0f} s. "
                             "Sensor tidak terbaca (cek ADS1115, kabel SDA/SCL, "
                             "dan Pmod 3 ke GND). AUTH memakai tegangan valid terakhir.")
        else:
            self._last_seen = (dump.seq_last, now)
        return lines

    def reset_anchor(self, battery_id: bytes):
        """Forget the seq anchor, e.g. after the chip was reset on purpose.
        Without this every dump is HISTORY_ROLLBACK until seq passes it."""
        record = self.db.lookup(battery_id)
        if record:
            record.seq_anchor = 0

    def verify_history(self, battery_id: bytes, nonce: bytes,
                       dump: HistoryDump) -> AuthStatus:
        """Verify summary, continuity, and per-record HMAC tags."""
        record = self.db.lookup(battery_id)
        if record is None:
            return AuthStatus.UNKNOWN_BATTERY
        if record.locked:
            return AuthStatus.BATTERY_LOCKED
        if self.db.is_nonce_used(nonce):
            return AuthStatus.REPLAY_DETECTED
        self.db.mark_nonce_used(nonce)

        seq_oldest = int(dump.seq_oldest) & 0xFFFFFFFF
        seq_last = int(dump.seq_last) & 0xFFFFFFFF
        summary = (bytes([SUMMARY_MSG_PREFIX]) + nonce + battery_id
                   + struct.pack('>II', seq_oldest, seq_last))
        expected_summary = hmac_sha256(record.key, summary)
        if dump.summary_tag != expected_summary:
            self._log_history(battery_id, AuthStatus.INVALID_HMAC, len(dump.records))
            return AuthStatus.INVALID_HMAC

        n = len(dump.records)
        if n == 0:
            empty_last = (seq_oldest - 1) & 0xFFFFFFFF
            if seq_last != empty_last:
                self._log_history(battery_id, AuthStatus.HISTORY_GAP, n)
                return AuthStatus.HISTORY_GAP
            if record.seq_anchor != 0:
                self._log_history(battery_id, AuthStatus.HISTORY_ROLLBACK, n)
                return AuthStatus.HISTORY_ROLLBACK
            self._log_history(battery_id, AuthStatus.VALID, n)
            return AuthStatus.VALID

        if seq_last < record.seq_anchor:
            self._log_history(battery_id, AuthStatus.HISTORY_ROLLBACK, n)
            return AuthStatus.HISTORY_ROLLBACK

        expected = [(seq_oldest + i) & 0xFFFFFFFF for i in range(n)]
        if n != ((seq_last - seq_oldest + 1) & 0xFFFFFFFF):
            self._log_history(battery_id, AuthStatus.HISTORY_GAP, n)
            return AuthStatus.HISTORY_GAP
        if [int(r.seq) & 0xFFFFFFFF for r in dump.records] != expected:
            self._log_history(battery_id, AuthStatus.HISTORY_GAP, n)
            return AuthStatus.HISTORY_GAP

        for rec in dump.records:
            message = (bytes([RECORD_MSG_PREFIX]) + battery_id
                       + struct.pack('>IH', rec.seq, rec.mv))
            if rec.tag != hmac_sha256(record.key, message):
                self._log_history(battery_id, AuthStatus.INVALID_HMAC, n)
                return AuthStatus.INVALID_HMAC

        truncated = seq_oldest > ((record.seq_anchor + 1) & 0xFFFFFFFF)
        record.seq_anchor = seq_last
        status = (AuthStatus.HISTORY_TRUNCATED if truncated
                  else AuthStatus.VALID)
        self._log_history(battery_id, status, n)
        return status

    def _log_history(self, battery_id: bytes, status: AuthStatus,
                     records: int):
        self.log.append({
            'status': status.name,
            'battery_id': battery_id.hex(),
            'records': records,
            'time': time.time(),
        })

    def lock_battery(self, battery_id: bytes):
        """Send LOCK command and update DB."""
        self._send_frame(Command.LOCK, b'')
        record = self.db.lookup(battery_id)
        if record:
            record.locked = True

    def unlock_battery(self, battery_id: bytes):
        """Send UNLOCK command and update DB."""
        self._send_frame(Command.UNLOCK, b'')
        record = self.db.lookup(battery_id)
        if record:
            record.locked = False


# -----------------------------------------------------------------------
# Demo scenarios
# -----------------------------------------------------------------------
def run_demo(station: Station):
    """Run demo sequence showing all auth scenarios."""
    print("=" * 60)
    print("SeBatt Demo — Secure Battery Authentication")
    print("=" * 60)

    # Scenario 1: Valid authentication
    print("\n[1] Valid authentication...")
    status, voltage, bid = station.authenticate()
    print(f"    Battery: {bid}")
    print(f"    Voltage: {voltage} mV")
    print(f"    Result:  {status.name}")
    assert status == AuthStatus.VALID

    # Scenario 2: Multiple valid auths
    print("\n[2] Multiple valid authentications (5x)...")
    for i in range(5):
        status, voltage, bid = station.authenticate()
        print(f"    Auth {i+1}: {status.name} ({voltage} mV)")
        assert status == AuthStatus.VALID

    # Scenario 3: Read and verify the signed history buffer
    print("\n[3] Read signed history...")
    status, dump = station.read_history(b'BAT\x01')
    if dump is None:
        print(f"    Result:  {status.name}")
    else:
        print(f"    Records: {len(dump.records)}")
        print(f"    Range:   seq {dump.seq_oldest}..{dump.seq_last}")
        print(f"    Result:  {status.name}")
    assert status in (AuthStatus.VALID, AuthStatus.HISTORY_TRUNCATED)

    # Scenario 4: Lock battery, try auth
    print("\n[4] Lock battery, attempt authentication...")
    station.lock_battery(b'BAT\x01')
    status, voltage, bid = station.authenticate()
    print(f"    Result: {status.name} (expected: BATTERY_LOCKED)")

    # Scenario 5: Unlock and retry
    print("\n[5] Unlock battery, re-authenticate...")
    station.unlock_battery(b'BAT\x01')
    status, voltage, bid = station.authenticate()
    print(f"    Result: {status.name}")

    print("\n" + "=" * 60)
    print(f"Demo complete. {len(station.log)} station transactions logged.")
    print("=" * 60)


def run_benchmark(station: Station, count: int = 100):
    """Throughput benchmark: count authentications."""
    print(f"Running {count} authentications...")
    t0 = time.time()
    ok = 0
    fail = 0
    for i in range(count):
        status, _, _ = station.authenticate()
        if status == AuthStatus.VALID:
            ok += 1
        else:
            fail += 1
        if (i + 1) % 10 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            print(f"  [{i+1}/{count}] {rate:.1f} auth/sec")

    elapsed = time.time() - t0
    rate = count / elapsed
    print(f"\nResults:")
    print(f"  Total:    {count}")
    print(f"  Valid:    {ok}")
    print(f"  Failed:   {fail}")
    print(f"  Time:     {elapsed:.2f} s")
    print(f"  Rate:     {rate:.1f} auth/sec")
    print(f"  Latency:  {elapsed/count*1000:.1f} ms/auth")


# -----------------------------------------------------------------------
# Offline test (no hardware)
# -----------------------------------------------------------------------
def run_offline_test(demo_mode: bool = False):
    """Test protocol logic without hardware."""
    from model.protocol import SeBattChip, Station as ModelStation

    print("=" * 60)
    print("SeBatt Demo (Offline Mode / Simulation)")
    print("============================================================")
    key = bytes(range(32))
    chip = SeBattChip(b'BAT\x01', key, voltage_mv=3700)
    station = ModelStation()
    station.register_battery(b'BAT\x01', key)

    # 1. Valid auth
    print("\n[Scenario 1] Legitimate Battery Swap Authentication")
    req = station.generate_challenge()
    print(f"  Station Nonce : {req.nonce[:8].hex()}... (32 bytes)")
    resp = chip.handle_auth_request(req)
    print(f"  Chip Battery  : {resp.battery_id.decode(errors='ignore')} (ID: {resp.battery_id.hex()})")
    print(f"  Chip Voltage  : {resp.voltage} mV (ADC measurement)")
    print(f"  Chip HMAC-256 : {resp.hmac_resp[:8].hex()}... (32 bytes)")
    status = station.verify_response(req, resp)
    print(f"  Verification  : {status.name} -> ACCESS GRANTED")
    assert status == AuthStatus.VALID

    # 2. Replay attack
    print("\n[Scenario 2] Replay Attack Detection")
    print("  Attacker replays recorded previous packet with identical nonce...")
    status = station.verify_response(req, resp)
    print(f"  Verification  : {status.name} -> REJECTED (Nonce reuse detected)")
    assert status == AuthStatus.REPLAY_DETECTED

    # 3. Voltage tampering
    print("\n[Scenario 3] In-Transit Telemetry Tampering")
    print("  Compromised BMS firmware alters voltage reading from 3700 mV to 4200 mV...")
    req2 = station.generate_challenge()
    resp2 = chip.handle_auth_request(req2)
    tampered = AuthResponse(
        battery_id=resp2.battery_id,
        voltage=4200,
        hmac_resp=resp2.hmac_resp,
    )
    status = station.verify_response(req2, tampered)
    print(f"  Verification  : {status.name} -> REJECTED (Cryptographic signature invalid)")
    assert status == AuthStatus.INVALID_HMAC

    # 4. Stolen/Locked battery
    print("\n[Scenario 4] Stolen / Recalled Battery Lockout")
    print("  Operator flags battery BAT01 as stolen in database...")
    station.lock_battery(b'BAT\x01')
    req3 = station.generate_challenge()
    resp3 = chip.handle_auth_request(req3)
    status = station.verify_response(req3, resp3)
    print(f"  Verification  : {status.name} -> REJECTED (Battery blocked)")
    assert status == AuthStatus.BATTERY_LOCKED

    # Unlock
    station.unlock_battery(b'BAT\x01')

    # 5. Signed history
    print("\n[Scenario 5] Signed History Dump")
    for mv in (3550, 3300, 2950):
        chip.set_voltage(mv)
        chip.sample_tick()
    status, dump = station.read_history(chip, b'BAT\x01')
    print(f"  Records       : {len(dump.records)}")
    print(f"  Seq range     : {dump.seq_oldest}..{dump.seq_last}")
    print(f"  Verification  : {status.name} -> HISTORY ACCEPTED")
    assert status == AuthStatus.VALID

    # 6. Benchmark
    print("\n[Benchmark] Running 1,000 simulated authentications...")
    t0 = time.time()
    for _ in range(1000):
        station.authenticate(chip)
    elapsed = time.time() - t0
    print(f"  Processed 1,000 authentications in {elapsed*1000:.2f} ms")
    print(f"  Throughput: {1000/elapsed:.0f} auth/sec (latency: {elapsed:.3f} ms/auth)")

    print("\n============================================================")
    print("Demo completed successfully. All security scenarios verified.")
    print("============================================================")


# -----------------------------------------------------------------------
# Port detection
# -----------------------------------------------------------------------
def find_uart_port() -> Optional[str]:
    """Auto-detect the FPGA UART, preferring the external CP210x/CH340.

    The KV260 PS console also appears as a USB-UART (FTDI), so blindly taking
    the first port can connect the station to the wrong UART. Prefer the
    external adapter used for Pmod J2, then fall back to any USB serial.
    """
    if serial is None:
        return None
    preferred = []
    fallback = []
    for p in serial.tools.list_ports.comports():
        # Ignore legacy motherboard ttyS* ports and the KV260 PS console.
        if p.device.startswith('/dev/ttyS'):
            continue
        desc = (p.description or '').lower()
        mfr = (p.manufacturer or '').lower()
        if 'ml carrier' in desc:
            continue
        if any(x in desc for x in ['cp210', 'ch340', 'ch34']) or 'silicon labs' in mfr:
            preferred.append(p.device)
        elif any(x in desc for x in ['digilent', 'ftdi', 'uart', 'usb']) or \
                any(x in mfr for x in ['digilent', 'ftdi']):
            fallback.append(p.device)
        elif 'ttyusb' in p.device.lower() or 'ttyacm' in p.device.lower():
            fallback.append(p.device)
    if preferred:
        return preferred[0]
    return fallback[0] if fallback else None


# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="SeBatt Station Emulator")
    parser.add_argument('--port', type=str, help='Serial port (e.g., /dev/ttyUSB1, COM3)')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    parser.add_argument('--demo', action='store_true', help='Run demo sequence')
    parser.add_argument('--benchmark', action='store_true', help='Run throughput benchmark')
    parser.add_argument('--history', action='store_true', help='Read and verify signed history')
    parser.add_argument('--count', type=int, default=100, help='Benchmark count')
    parser.add_argument('--offline', action='store_true', help='Run offline test (no hardware)')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    parser.add_argument('--profil', choices=sorted(PROFILES), default=DEFAULT_PROFILE,
                        help='Battery profile for the health card: sel (knob on A0 as one '
                             'Li-ion cell) or aki12v (12 V battery through the casing divider)')
    args = parser.parse_args()

    if args.offline:
        run_offline_test(demo_mode=args.demo)
        return

    port = args.port or find_uart_port()
    if port is None:
        if args.demo:
            print("[INFO] No hardware board detected on USB-UART. Running simulated Demo Day suite...\n")
            run_offline_test(demo_mode=True)
            return
        print("No FPGA USB-UART board detected. Connect Nexys A7 via micro-USB, specify --port, or use --offline.")
        sys.exit(1)

    print(f"Connecting to {port} at {args.baud} baud...")
    try:
        station = Station(port, args.baud)
    except serial.SerialException as e:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        print(f"Tidak bisa membuka {port}: {e}")
        print(f"Port yang tersedia: {', '.join(ports) if ports else '(tidak ada)'}")
        print("Cek kabel CP2102, nomor COM di Device Manager, dan pastikan "
              "PuTTY atau station lain tidak sedang memakai port itu.")
        sys.exit(1)
    station.profile = PROFILES[args.profil]

    try:
        if args.demo:
            run_demo(station)
        elif args.history:
            status, dump = station.read_history(b'BAT\x01')
            for line in station.history_report(status, dump):
                print(line)
        elif args.benchmark:
            run_benchmark(station, args.count)
        elif args.interactive:
            interactive_mode(station)
        else:
            # Single auth
            status, voltage, bid = station.authenticate()
            print(f"Battery: {bid}")
            print(f"Voltage: {voltage} mV")
            print(f"Result:  {status.name}")
    finally:
        station.close()


def interactive_mode(station: Station):
    """Interactive CLI for demo."""
    print("SeBatt Interactive Station")
    print("Commands: auth, history, status, lock, unlock, reset-anchor, bench, quit")
    print("BMS curang: attack tamper [seq] [mV baterai] | attack delete [n] | "
          "attack cut [n] | attack replay")

    while True:
        try:
            cmd = input("\nstation> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if cmd in ('q', 'quit', 'exit'):
            break
        try:
            _run_command(station, cmd)
        except (TimeoutError, ValueError, OSError) as e:
            # The board did not answer or the adapter was unplugged; keep the
            # session (and its seq anchor) alive instead of exiting.
            print(f"  Tidak ada jawaban yang benar dari chip: {e}")
            print("  Cek LED heartbeat, kabel CP2102, dan apakah bitstream masih termuat.")


def _run_command(station: Station, cmd: str):
    """One interactive command (everything except quit)."""
    if cmd in ('a', 'auth'):
        status, voltage, bid = station.authenticate()
        if status == AuthStatus.BATTERY_LOCKED:
            print(f"  Battery: {bid}  Chip terkunci → BATTERY_LOCKED (DITOLAK). "
                  "Ketik unlock untuk membuka.")
        else:
            batt_v = f"{to_battery_mv(voltage, station.profile) / 1000:.2f}".replace(".", ",")
            print(f"  Battery: {bid}  Voltage: {batt_v} V (pin {voltage} mV)  "
                  f"→ {status.name} ({verdict(status)})")
    elif cmd == 'lock':
        station.lock_battery(b'BAT\x01')
        print("  Battery locked")
    elif cmd == 'unlock':
        station.unlock_battery(b'BAT\x01')
        print("  Battery unlocked")
    elif cmd in ('s', 'status'):
        locked, fails = station.query_status()
        print(f"  Chip: {'LOCKED' if locked else 'unlocked'}, fail_cnt={fails}")
    elif cmd == 'reset-anchor':
        station.reset_anchor(b'BAT\x01')
        print("  Seq anchor cleared (use after a deliberate chip reset)")
    elif cmd.startswith('attack'):
        parts = cmd.split()
        if len(parts) < 2 or parts[1] not in ('tamper', 'delete', 'cut', 'replay'):
            print("  Usage: attack tamper [seq] [mV baterai] | attack delete [n] | "
                  "attack cut [n] | attack replay")
            return
        mode, args = parts[1], [int(x) for x in parts[2:] if x.isdigit()]
        kwargs = {}
        if mode == 'tamper':
            if len(args) >= 1:
                kwargs['seq'] = args[0]
            if len(args) >= 2:
                kwargs['mv'] = args[1]
        elif mode in ('delete', 'cut') and args:
            kwargs['count'] = args[0]
        status, desc = station.read_history_attacked(b'BAT\x01', mode, **kwargs)
        if status is None:
            print(f"  {desc}")
        else:
            print(f"  BMS curang: {desc}")
            print(f"  Stasiun  : {status.name} -> {verdict(status)}")
            try:
                locked, fails = station.query_status()
                if locked:
                    print("  Chip     : TERKUNCI setelah 3 penolakan berturut-turut. "
                          "Ketik unlock untuk membuka.")
                else:
                    print(f"  Chip     : gagal berturut-turut {fails}/3 "
                          "(history yang VALID mengembalikan ke 0)")
            except (TimeoutError, ValueError):
                pass
    elif cmd in ('h', 'history'):
        status, dump = station.read_history(b'BAT\x01')
        for line in station.history_report(status, dump):
            print(f"  {line}")
    elif cmd in ('b', 'bench'):
        run_benchmark(station, 50)
    elif cmd == 'log':
        for entry in station.log[-10:]:
            print(f"  {entry}")
    else:
        print("  Unknown command")


if __name__ == '__main__':
    main()
