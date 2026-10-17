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
    AuthRequest, AuthResponse,
)


# -----------------------------------------------------------------------
# Identity database
# -----------------------------------------------------------------------
@dataclass
class BatteryRecord:
    battery_id: bytes
    key: bytes
    locked: bool = False
    auth_count: int = 0


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

        # Register default battery (matches firmware)
        default_key = bytes(range(32))
        self.db.register(b'BAT\x01', default_key)

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    # --- Low-level UART I/O ---

    def _send_frame(self, cmd: int, payload: bytes):
        """Send wire protocol frame."""
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

    def authenticate(self) -> tuple:
        """
        Run full authentication:
          1. Generate random nonce
          2. Send AUTH_REQ to chip
          3. Receive AUTH_RESP
          4. Verify HMAC

        Returns: (AuthStatus, voltage, battery_id_hex)
        """
        # Generate nonce
        nonce = os.urandom(32)

        # Send AUTH_REQ
        self._send_frame(Command.AUTH_REQ, nonce)

        # Receive AUTH_RESP
        cmd, payload = self._recv_frame()
        if cmd != Command.AUTH_RESP:
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
            msg = nonce + battery_id + struct.pack('>H', voltage)
            expected = hmac_sha256(record.key, msg)
            if hmac_resp == expected:
                status = AuthStatus.VALID
                record.auth_count += 1
            else:
                status = AuthStatus.INVALID_HMAC

        self.log.append({
            'status': status.name,
            'battery_id': battery_id.hex(),
            'voltage': voltage,
            'time': time.time(),
        })

        return status, voltage, battery_id.hex()

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

    # Scenario 3: Lock battery, try auth
    print("\n[3] Lock battery, attempt authentication...")
    station.lock_battery(b'BAT\x01')
    status, voltage, bid = station.authenticate()
    print(f"    Result: {status.name} (expected: BATTERY_LOCKED)")

    # Scenario 4: Unlock and retry
    print("\n[4] Unlock battery, re-authenticate...")
    station.unlock_battery(b'BAT\x01')
    status, voltage, bid = station.authenticate()
    print(f"    Result: {status.name}")

    print("\n" + "=" * 60)
    print(f"Demo complete. {len(station.log)} auth attempts logged.")
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

    # 5. Benchmark
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
    """Auto-detect FPGA UART port (USB-UART only)."""
    if serial is None:
        return None
    ports = serial.tools.list_ports.comports()
    for p in ports:
        # Ignore legacy motherboard ttyS* ports
        if p.device.startswith('/dev/ttyS'):
            continue
        desc = (p.description or '').lower()
        mfr = (p.manufacturer or '').lower()
        # Digilent / FTDI / CP210x / CH340 / USB serial
        if any(x in desc for x in ['digilent', 'ftdi', 'cp210', 'ch34', 'uart', 'usb']):
            return p.device
        if any(x in mfr for x in ['digilent', 'ftdi', 'silicon labs']):
            return p.device
        if 'ttyusb' in p.device.lower() or 'ttyacm' in p.device.lower():
            return p.device
    return None


# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="SeBatt Station Emulator")
    parser.add_argument('--port', type=str, help='Serial port (e.g., /dev/ttyUSB1, COM3)')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    parser.add_argument('--demo', action='store_true', help='Run demo sequence')
    parser.add_argument('--benchmark', action='store_true', help='Run throughput benchmark')
    parser.add_argument('--count', type=int, default=100, help='Benchmark count')
    parser.add_argument('--offline', action='store_true', help='Run offline test (no hardware)')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
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
    station = Station(port, args.baud)

    try:
        if args.demo:
            run_demo(station)
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
    print("Commands: auth, lock, unlock, bench, quit")

    while True:
        try:
            cmd = input("\nstation> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if cmd in ('q', 'quit', 'exit'):
            break
        elif cmd in ('a', 'auth'):
            status, voltage, bid = station.authenticate()
            print(f"  Battery: {bid}  Voltage: {voltage}mV  → {status.name}")
        elif cmd == 'lock':
            station.lock_battery(b'BAT\x01')
            print("  Battery locked")
        elif cmd == 'unlock':
            station.unlock_battery(b'BAT\x01')
            print("  Battery unlocked")
        elif cmd in ('b', 'bench'):
            run_benchmark(station, 50)
        elif cmd == 'log':
            for entry in station.log[-10:]:
                print(f"  {entry}")
        else:
            print("  Unknown command")


if __name__ == '__main__':
    main()
