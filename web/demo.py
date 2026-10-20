from __future__ import annotations

import struct
import threading
import time
from dataclasses import dataclass
from typing import Optional

from model.hmac import hmac_sha256

BATTERY_ID = b"BAT\x01"
BATTERY_LABEL = "BAT-0001"
KEY = bytes(range(32))
BUFFER_SIZE = 64
LOW_MV = 2500
HIGH_MV = 4000
ARM_MV = 3000
RECORD_PREFIX = 0x53

SEED_MV = [
    4160, 4120, 4080, 4020, 3970, 3910, 3860, 3800,
    3750, 3700, 3660, 3610, 3560, 3500, 3440, 3370,
]


def _fmt_v(mv: int) -> str:
    return f"{mv / 1000:.1f}".replace(".", ",") + " V"


@dataclass
class Record:
    seq: int
    mv: int
    tag: bytes
    original_mv: int
    deleted: bool = False
    tampered: bool = False

    def public(self) -> dict:
        return {
            "seq": self.seq,
            "mv": self.mv,
            "original_mv": self.original_mv,
            "tag": self.tag.hex()[:16],
            "deleted": self.deleted,
            "tampered": self.tampered,
        }


class DemoState:
    def __init__(self):
        self._lock = threading.RLock()
        self.reset()

    def reset(self) -> dict:
        with self._lock:
            self.records: list[Record] = []
            self.next_seq = 1
            self.last_seq = 0
            self.locked = False
            self.fail_streak = 0
            self.health: Optional[dict] = None
            self.health_status = "unverified"
            self.last_result: Optional[dict] = None
            self.logs: list[dict] = []
            self.verified_at: Optional[float] = None
            self.power_cycled = False
            for mv in SEED_MV:
                self._append(mv)
            return self.state()

    def _tag(self, seq: int, mv: int) -> bytes:
        message = (
            bytes([RECORD_PREFIX])
            + BATTERY_ID
            + struct.pack(">I", seq)
            + struct.pack(">H", mv)
        )
        return hmac_sha256(KEY, message)

    def _append(self, mv: int) -> Record:
        seq = self.next_seq
        rec = Record(seq=seq, mv=mv, tag=self._tag(seq, mv), original_mv=mv)
        self.records.append(rec)
        self.next_seq += 1
        if len(self.records) > BUFFER_SIZE:
            self.records.pop(0)
        return rec

    def _find(self, seq: int) -> Optional[Record]:
        for rec in self.records:
            if rec.seq == seq:
                return rec
        return None

    def _health(self) -> Optional[dict]:
        samples = [rec for rec in self.records if not rec.deleted]
        if not samples:
            return None
        cycles = 0
        armed = False
        for rec in sorted(samples, key=lambda r: r.seq):
            if rec.mv < ARM_MV:
                armed = True
            elif rec.mv > HIGH_MV and armed:
                cycles += 1
                armed = False
        return {
            "cycles": cycles,
            "deep": sum(1 for rec in samples if rec.mv < LOW_MV),
            "min_mv": min(rec.mv for rec in samples),
            "max_mv": max(rec.mv for rec in samples),
            "samples": len(samples),
            "verified_seq": self.next_seq - 1,
        }

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
        self.logs.append({
            "at": result["at"],
            "status": result["status"],
            "code": result["code"],
            "title": result["title"],
            "message": result["message"],
        })
        if len(self.logs) > 24:
            self.logs = self.logs[-24:]

    def _reject(self, result: dict) -> None:
        self.fail_streak += 1
        if self.fail_streak >= 3 and not self.locked:
            self.locked = True
            result["message"] += " Chip terkunci setelah 3 penolakan berturut-turut."
            result["locked_now"] = True
        self.health = None
        self.health_status = "untrusted"
        self.last_result = result
        self._log(result)

    def record(self, mv: int) -> dict:
        with self._lock:
            mv = max(0, min(5000, int(mv)))
            self.power_cycled = False
            self._append(mv)
            return self.state()

    def swap(self) -> dict:
        with self._lock:
            now = time.time()
            chip_seq = self.next_seq - 1

            if self.locked:
                result = self._result(
                    "rejected", "BATTERY_LOCKED", "DITOLAK",
                    "Chip terkunci dan tidak merespons. Buka kunci untuk melanjutkan demo.",
                    chip_seq, now,
                )
                self.health = None
                self.health_status = "untrusted"
                self.last_result = result
                self._log(result)
                return self.state()

            if chip_seq < self.last_seq:
                result = self._result(
                    "rejected", "ROLLBACK", "DITOLAK",
                    f"Penghitung diputar balik: seq {chip_seq} lebih kecil dari "
                    f"{self.last_seq} yang tercatat di basis data.",
                    chip_seq, now,
                )
                self._reject(result)
                return self.state()

            start = self.last_seq + 1
            truncated = False
            if self.records and start < self.records[0].seq:
                start = self.records[0].seq
                truncated = True

            missing = []
            bad = []
            for seq in range(start, chip_seq + 1):
                rec = self._find(seq)
                if rec is None or rec.deleted:
                    missing.append(seq)
                    continue
                if self._tag(seq, rec.mv) != rec.tag:
                    bad.append(rec)

            if missing:
                shown = ", ".join(str(seq) for seq in missing[:3])
                if len(missing) > 3:
                    shown += f", +{len(missing) - 3}"
                result = self._result(
                    "rejected", "HISTORY_GAP", "DITOLAK",
                    f"Catatan seq {shown} hilang dari riwayat. Urutan nomor tidak lengkap.",
                    missing[0], now,
                )
                self._reject(result)
                return self.state()

            if bad:
                rec = bad[0]
                result = self._result(
                    "rejected", "INVALID_HMAC", "DITOLAK",
                    f"Data seq {rec.seq} diubah dari {_fmt_v(rec.original_mv)} "
                    f"menjadi {_fmt_v(rec.mv)} tanpa tanda tangan baru.",
                    rec.seq, now,
                )
                self._reject(result)
                return self.state()

            if chip_seq == self.last_seq:
                message = "Tidak ada catatan baru. Riwayat terakhir tetap utuh."
            else:
                message = (
                    f"{chip_seq - self.last_seq} catatan baru terverifikasi. "
                    f"Riwayat seq 1–{chip_seq} utuh."
                )
                if truncated:
                    message += " Catatan lama tertimpa buffer, bukan kecurangan."

            self.last_seq = chip_seq
            self.fail_streak = 0
            self.health = self._health()
            self.health_status = "trusted"
            self.verified_at = now
            if self.health is not None:
                self.health["verified_seq"] = chip_seq
            result = self._result("accepted", "VALID", "DITERIMA", message, chip_seq, now)
            self.last_result = result
            self._log(result)
            return self.state()

    def _new_records(self) -> list[Record]:
        if self.last_seq == 0:
            return []
        return [
            rec for rec in self.records
            if rec.seq > self.last_seq and not rec.deleted
        ]

    def attack_delete(self) -> dict:
        with self._lock:
            if self.last_seq == 0:
                return {"ok": False, "message": "Verifikasi riwayat awal dengan Tukar baterai dulu."}
            candidates = self._new_records()
            if not candidates:
                return {"ok": False, "message": "Tidak ada catatan baru. Catat sampel dulu."}
            target = max(candidates, key=lambda rec: rec.seq)
            target.deleted = True
            return {"ok": True, "message": f"Catatan seq {target.seq} dihapus oleh BMS curang.", "state": self.state()}

    def attack_tamper(self) -> dict:
        with self._lock:
            if self.last_seq == 0:
                return {"ok": False, "message": "Verifikasi riwayat awal dengan Tukar baterai dulu."}
            candidates = [rec for rec in self._new_records() if not rec.tampered]
            if not candidates:
                return {"ok": False, "message": "Tidak ada catatan baru untuk diubah. Catat sampel dulu."}
            target = max(candidates, key=lambda rec: rec.seq)
            target.tampered = True
            target.mv = 3600 if target.original_mv != 3600 else 4200
            return {
                "ok": True,
                "message": f"Catatan seq {target.seq} diubah dari "
                           f"{_fmt_v(target.original_mv)} menjadi {_fmt_v(target.mv)}.",
                "state": self.state(),
            }

    def restore(self) -> dict:
        with self._lock:
            for rec in self.records:
                rec.deleted = False
                rec.tampered = False
                rec.mv = rec.original_mv
            self.last_result = None
            self.fail_streak = 0
            if self.last_seq > 0 and self.health is not None:
                self.health_status = "trusted"
            else:
                self.health = None
                self.health_status = "unverified"
            return self.state()

    def unlock(self) -> dict:
        with self._lock:
            self.locked = False
            self.fail_streak = 0
            self.last_result = None
            if self.last_seq > 0 and self.health is not None and self.health_status == "trusted":
                self.health_status = "trusted"
            else:
                self.health = None
                self.health_status = "unverified"
            return self.state()

    def power_cycle(self) -> dict:
        with self._lock:
            self.records = []
            self.next_seq = 1
            self.locked = False
            self.fail_streak = 0
            self.health = None
            self.health_status = "unverified"
            self.last_result = None
            self.power_cycled = True
            return self.state()

    def state(self) -> dict:
        with self._lock:
            chip_seq = self.next_seq - 1
            pending = max(0, chip_seq - self.last_seq)
            return {
                "battery": {
                    "id": BATTERY_LABEL,
                    "locked": self.locked,
                },
                "mode": "simulasi",
                "last_seq": self.last_seq,
                "chip_seq": chip_seq,
                "pending": pending,
                "buffer_size": BUFFER_SIZE,
                "records": [rec.public() for rec in self.records],
                "health": self.health,
                "health_status": self.health_status,
                "last_result": self.last_result,
                "fail_streak": self.fail_streak,
                "logs": self.logs[-8:],
                "verified_at": self.verified_at,
                "power_cycled": self.power_cycled,
            }
