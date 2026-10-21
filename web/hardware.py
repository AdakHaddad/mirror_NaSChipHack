"""Dashboard state backed by a real SeBatt FPGA over UART.

The browser still talks to the same JSON API as the simulation. This adapter
keeps the dashboard state in the same shape, but every authentication, history
dump, and verdict comes from ``model.station.Station`` and the board.

The FPGA samples the ADS1115 itself. ``refresh_live`` reads the signed history
without verifying it (so the chart can show new samples); ``swap`` performs the
real authentication and history verification and only then moves the database
anchor.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from model.protocol import AuthStatus, HistoryDump, HistoryRecord
from model.station import Station
from web.demo import (
    ARM_MV,
    BATTERY_ID,
    BATTERY_LABEL,
    BUFFER_SIZE,
    HIGH_MV,
    LOW_MV,
)


def _fmt_v(mv: int) -> str:
    return f"{mv / 1000:.1f}".replace(".", ",") + " V"


def _status_text(status: AuthStatus) -> str:
    return {
        AuthStatus.INVALID_HMAC: "tanda tangan HMAC tidak cocok",
        AuthStatus.REPLAY_DETECTED: "nonce sudah pernah dipakai",
        AuthStatus.BATTERY_LOCKED: "chip terkunci",
        AuthStatus.UNKNOWN_BATTERY: "baterai tidak terdaftar",
        AuthStatus.HISTORY_GAP: "ada catatan yang hilang",
        AuthStatus.HISTORY_ROLLBACK: "nomor urut lebih kecil dari jangkar",
        AuthStatus.HISTORY_TRUNCATED: "catatan lama tertimpa buffer",
        AuthStatus.VALID: "valid",
    }.get(status, status.name)


class HardwareState:
    """Dashboard state for a real FPGA connected through a serial port."""

    def __init__(self, station: Station, port: str = "", baud: int = 115200):
        self.station = station
        self.port = port
        self.baud = baud
        self._lock = threading.RLock()
        self._last_error: Optional[str] = None
        self._last_dump: Optional[HistoryDump] = None
        self._verified_dump: Optional[HistoryDump] = None
        self._attack: Optional[dict] = None
        self._last_result: Optional[dict] = None
        self._logs: list[dict] = []
        self._health: Optional[dict] = None
        self._health_status = "unverified"
        self._last_seq = 0
        self._chip_seq = 0
        self._verified_seq: Optional[int] = None
        self._fail_streak = 0
        self._locked = False
        self._voltage_mv: Optional[int] = None
        self._verified_at: Optional[float] = None
        self.refresh_live()

    # --- helpers -----------------------------------------------------
    def _record(self):
        return self.station.db.lookup(BATTERY_ID)

    def _read_anchor(self) -> int:
        record = self._record()
        return int(record.seq_anchor) if record else 0

    def _query_status(self) -> None:
        try:
            locked, fails = self.station.query_status()
            self._locked = bool(locked)
            self._fail_streak = int(fails)
            self._last_error = None
        except Exception as exc:  # keep the last known state on a transient error
            self._last_error = str(exc)

    @staticmethod
    def _display_chip_seq(dump: HistoryDump) -> int:
        seq_last = int(dump.seq_last) & 0xFFFFFFFF
        # Empty RTL buffer reports seq_last = seq_oldest - 1 = 0xFFFFFFFF.
        if not dump.records and seq_last == 0xFFFFFFFF:
            return 0
        return seq_last

    @staticmethod
    def _health_from(records: list[HistoryRecord], verified_seq: int) -> Optional[dict]:
        if not records:
            return None
        cycles = 0
        armed = False
        for rec in sorted(records, key=lambda item: item.seq):
            if rec.mv < ARM_MV:
                armed = True
            elif rec.mv > HIGH_MV and armed:
                cycles += 1
                armed = False
        return {
            "cycles": cycles,
            "deep": sum(1 for rec in records if rec.mv < LOW_MV),
            "min_mv": min(rec.mv for rec in records),
            "max_mv": max(rec.mv for rec in records),
            "samples": len(records),
            "verified_seq": verified_seq,
        }

    def _apply_attack(self, dump: HistoryDump) -> HistoryDump:
        if not self._attack:
            return dump
        records = [
            HistoryRecord(seq=rec.seq, mv=rec.mv, tag=rec.tag)
            for rec in dump.records
        ]
        if self._attack["kind"] == "delete":
            records = [rec for rec in records if rec.seq != self._attack["seq"]]
        elif self._attack["kind"] == "tamper":
            for rec in records:
                if rec.seq == self._attack["seq"]:
                    rec.mv = self._attack["mv"]
        return HistoryDump(
            battery_id=dump.battery_id,
            seq_oldest=dump.seq_oldest,
            seq_last=dump.seq_last,
            records=records,
            summary_tag=dump.summary_tag,
        )

    def _display_records(self) -> list[dict]:
        if self._last_dump is None:
            return []
        attack_seq = self._attack["seq"] if self._attack else None
        display = []
        for rec in self._last_dump.records:
            deleted = bool(self._attack and self._attack["kind"] == "delete"
                           and rec.seq == attack_seq)
            tampered = bool(self._attack and self._attack["kind"] == "tamper"
                            and rec.seq == attack_seq)
            mv = self._attack["mv"] if tampered else rec.mv
            display.append({
                "seq": rec.seq,
                "mv": mv,
                "original_mv": rec.mv,
                "tag": rec.tag.hex()[:16],
                "deleted": deleted,
                "tampered": tampered,
            })
        return display

    def _result(self, status: str, code: str, title: str, message: str,
                seq: Optional[int], at: float) -> dict:
        return {
            "status": status,
            "code": code,
            "title": title,
            "message": message,
            "seq": seq,
            "at": at,
        }

    def _log(self, result: dict) -> None:
        self._logs.append({
            "at": result["at"],
            "status": result["status"],
            "code": result["code"],
            "title": result["title"],
            "message": result["message"],
        })
        if len(self._logs) > 24:
            self._logs = self._logs[-24:]

    def _finish(self, result: dict) -> None:
        self._last_result = result
        self._log(result)

    # --- public operations ------------------------------------------
    def refresh_live(self) -> dict:
        """Read the latest history without verifying it."""
        with self._lock:
            try:
                transport, _nonce, dump = self.station.read_history_raw(BATTERY_ID)
            except Exception as exc:
                self._last_error = str(exc)
                return self.state()
            if dump is None:
                if transport == AuthStatus.BATTERY_LOCKED:
                    self._locked = True
                    self._last_error = None
                    self._query_status()
                else:
                    self._last_error = (
                        f"riwayat tidak tersedia ({_status_text(transport)})")
                return self.state()

            self._last_dump = dump
            self._chip_seq = self._display_chip_seq(dump)
            if dump.records:
                self._voltage_mv = int(dump.records[-1].mv)
            self._last_seq = self._read_anchor()
            self._last_error = None
            self._query_status()
            return self.state()

    def swap(self) -> dict:
        """Authenticate, fetch history, verify it, and return the dashboard state."""
        with self._lock:
            now = time.time()
            was_locked = self._locked
            try:
                auth_status, voltage, _bid = self.station.authenticate(report=False)
            except Exception as exc:
                result = self._result(
                    "rejected", "LINK_ERROR", "DITOLAK",
                    f"Tidak dapat menghubungi FPGA: {exc}", None, now,
                )
                self._last_error = str(exc)
                self._health = None
                self._health_status = "untrusted"
                self._finish(result)
                return self.state()

            if auth_status != AuthStatus.VALID:
                self._locked = auth_status == AuthStatus.BATTERY_LOCKED
                if auth_status != AuthStatus.BATTERY_LOCKED:
                    try:
                        self.station.report_result(auth_status)
                    except Exception as exc:
                        self._last_error = str(exc)
                result = self._result(
                    "rejected", auth_status.name, "DITOLAK",
                    f"Autentikasi gagal: {_status_text(auth_status)}.",
                    self._chip_seq, now,
                )
                self._health = None
                self._health_status = "untrusted"
                self._finish(result)
                self._query_status()
                return self.state()

            try:
                transport, nonce, dump = self.station.read_history_raw(BATTERY_ID)
            except Exception as exc:
                result = self._result(
                    "rejected", "LINK_ERROR", "DITOLAK",
                    f"Gagal membaca riwayat dari FPGA: {exc}", self._chip_seq, now,
                )
                self._last_error = str(exc)
                self._health = None
                self._health_status = "untrusted"
                self._finish(result)
                return self.state()

            if dump is None:
                result = self._result(
                    "rejected", transport.name, "DITOLAK",
                    f"Riwayat tidak dapat dibaca: {_status_text(transport)}.",
                    self._chip_seq, now,
                )
                self._health = None
                self._health_status = "untrusted"
                self._finish(result)
                self._query_status()
                return self.state()

            self._last_dump = dump
            self._chip_seq = self._display_chip_seq(dump)
            self._voltage_mv = int(dump.records[-1].mv) if dump.records else int(voltage)
            verify_dump = self._apply_attack(dump)

            try:
                hist_status = self.station.verify_history(
                    BATTERY_ID, nonce, verify_dump)
                self.station.report_result(hist_status)
            except Exception as exc:
                result = self._result(
                    "rejected", "LINK_ERROR", "DITOLAK",
                    f"Verifikasi riwayat gagal: {exc}", self._chip_seq, now,
                )
                self._last_error = str(exc)
                self._health = None
                self._health_status = "untrusted"
                self._finish(result)
                return self.state()

            self._last_seq = self._read_anchor()
            if hist_status in (AuthStatus.VALID, AuthStatus.HISTORY_TRUNCATED):
                self._verified_dump = dump
                self._health = self._health_from(dump.records, dump.seq_last)
                self._health_status = "trusted"
                self._verified_at = time.time()
                self._verified_seq = self._chip_seq
                suffix = ""
                if hist_status == AuthStatus.HISTORY_TRUNCATED:
                    suffix = " Catatan lama tertimpa buffer."
                if self._chip_seq == 0:
                    message = "Autentikasi valid. Riwayat masih kosong."
                else:
                    message = (
                        f"Autentikasi valid. {len(dump.records)} catatan "
                        f"diverifikasi (seq {dump.seq_oldest}–{dump.seq_last})."
                        f"{suffix}"
                    )
                result = self._result(
                    "accepted", hist_status.name, "DITERIMA", message,
                    self._chip_seq, now,
                )
            else:
                self._health = None
                self._health_status = "untrusted"
                result = self._result(
                    "rejected", hist_status.name, "DITOLAK",
                    f"Riwayat ditolak: {_status_text(hist_status)}.",
                    self._chip_seq, now,
                )

            self._finish(result)
            self._query_status()
            if not was_locked and self._locked:
                result["locked_now"] = True
            return self.state()

    def record(self, mv: int) -> dict:
        """The FPGA samples by itself; keep the API working by refreshing."""
        return self.refresh_live()

    def attack_delete(self) -> dict:
        with self._lock:
            if self._last_dump is None:
                self.refresh_live()
            if self._last_dump is None:
                return {"ok": False, "message": "Belum ada riwayat dari FPGA."}
            candidates = [rec for rec in self._last_dump.records
                          if rec.seq > self._last_seq]
            if not candidates:
                return {"ok": False,
                        "message": "Tidak ada catatan baru. Tunggu sampling FPGA dulu."}
            target = max(candidates, key=lambda rec: rec.seq)
            self._attack = {"kind": "delete", "seq": target.seq}
            return {
                "ok": True,
                "message": f"BMS curang menghapus catatan seq {target.seq}.",
                "state": self.state(),
            }

    def attack_tamper(self) -> dict:
        with self._lock:
            if self._last_dump is None:
                self.refresh_live()
            if self._last_dump is None:
                return {"ok": False, "message": "Belum ada riwayat dari FPGA."}
            candidates = [rec for rec in self._last_dump.records
                          if rec.seq > self._last_seq]
            if not candidates:
                return {"ok": False,
                        "message": "Tidak ada catatan baru. Tunggu sampling FPGA dulu."}
            target = max(candidates, key=lambda rec: rec.seq)
            new_mv = 3600 if target.mv != 3600 else 4200
            self._attack = {"kind": "tamper", "seq": target.seq, "mv": new_mv}
            return {
                "ok": True,
                "message": (f"BMS curang mengubah seq {target.seq} dari "
                            f"{_fmt_v(target.mv)} menjadi {_fmt_v(new_mv)}."),
                "state": self.state(),
            }

    def restore(self) -> dict:
        with self._lock:
            self._attack = None
            self._last_result = None
            if self._verified_dump is not None:
                self._health = self._health_from(
                    self._verified_dump.records, self._verified_dump.seq_last)
                self._health_status = "trusted"
            else:
                self._health = None
                self._health_status = "unverified"
            return self.state()

    def unlock(self) -> dict:
        with self._lock:
            try:
                self.station.unlock_battery(BATTERY_ID)
                self._locked = False
                self._fail_streak = 0
                self._last_result = None
                self._last_error = None
            except Exception as exc:
                self._last_error = str(exc)
            return self.state()

    def reset(self) -> dict:
        with self._lock:
            self._attack = None
            self._last_result = None
            self._logs = []
            self._health = None
            self._health_status = "unverified"
            self._verified_dump = None
            self._verified_seq = None
            return self.refresh_live()

    def power_cycle(self) -> dict:
        return {
            "ok": False,
            "message": "Mode FPGA: cabut daya tidak tersedia lewat dashboard. "
                       "Muat ulang bitstream atau tekan tombol reset board.",
        }

    def state(self) -> dict:
        with self._lock:
            if self._verified_seq is None:
                pending = (len(self._last_dump.records)
                           if self._last_dump else 0)
            else:
                pending = max(0, self._chip_seq - self._verified_seq)
            return {
                "battery": {
                    "id": BATTERY_LABEL,
                    "locked": self._locked,
                },
                "mode": "fpga",
                "hardware": {
                    "port": self.port,
                    "baud": self.baud,
                    "connected": self._last_error is None,
                    "error": self._last_error,
                },
                "last_seq": self._last_seq,
                "chip_seq": self._chip_seq,
                "voltage_mv": self._voltage_mv,
                "pending": pending,
                "buffer_size": BUFFER_SIZE,
                "records": self._display_records(),
                "health": self._health,
                "health_status": self._health_status,
                "last_result": self._last_result,
                "fail_streak": self._fail_streak,
                "logs": self._logs[-8:],
                "verified_at": self._verified_at,
                "power_cycled": False,
            }
