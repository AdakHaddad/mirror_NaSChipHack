import os
import struct
import unittest

from model.hmac import hmac_sha256
from model.protocol import (
    AUTH_MSG_PREFIX,
    AuthRequest,
    AuthStatus,
    SeBattChip,
)
from model.station import IdentityDB, Station
from web.hardware import HardwareState

BATTERY_ID = b"BAT\x01"
KEY = bytes(range(32))


class FakeStation(Station):
    """A Station-compatible object backed by the in-memory chip model."""

    def __init__(self):
        self.db = IdentityDB()
        self.db.register(BATTERY_ID, KEY)
        self.chip = SeBattChip(BATTERY_ID, KEY, voltage_mv=3700)
        self.log = []
        self.last_battery_id = BATTERY_ID
        self.report_results = True

    def sample(self, mv):
        self.chip.set_voltage(mv)
        self.chip.sample_tick()
        return mv

    def authenticate(self, report=True):
        if self.chip.locked:
            return AuthStatus.BATTERY_LOCKED, 0, BATTERY_ID.hex()
        nonce = os.urandom(32)
        response = self.chip.handle_auth_request(AuthRequest(nonce=nonce))
        message = (bytes([AUTH_MSG_PREFIX]) + nonce + BATTERY_ID
                   + struct.pack(">H", response.voltage))
        expected = hmac_sha256(KEY, message)
        if response.hmac_resp != expected:
            if report:
                self.report_result(AuthStatus.INVALID_HMAC)
            return AuthStatus.INVALID_HMAC, 0, BATTERY_ID.hex()
        if report:
            self.report_result(AuthStatus.VALID)
        return AuthStatus.VALID, response.voltage, BATTERY_ID.hex()

    def read_history_raw(self, battery_id=None, nonce=None):
        nonce = nonce or os.urandom(32)
        dump = self.chip.handle_read_hist_request(nonce)
        if dump is None:
            return AuthStatus.BATTERY_LOCKED, nonce, None
        dump.battery_id = battery_id or BATTERY_ID
        return AuthStatus.VALID, nonce, dump

    def query_status(self):
        return self.chip.locked, self.chip.fail_count

    def report_result(self, status):
        self.chip.handle_result(status)

    def unlock_battery(self, battery_id):
        self.chip.unlock()


class HardwareStateTests(unittest.TestCase):
    def setUp(self):
        self.station = FakeStation()
        self.state = HardwareState(self.station, port="/dev/ttyUSB0")

    def test_initial_state_is_fpga_and_empty(self):
        state = self.state.state()
        self.assertEqual(state["mode"], "fpga")
        self.assertEqual(state["battery"]["id"], "BAT-0001")
        self.assertEqual(state["chip_seq"], 0)
        self.assertEqual(state["pending"], 0)
        self.assertEqual(state["records"], [])
        self.assertEqual(state["health_status"], "unverified")
        self.assertEqual(state["hardware"]["port"], "/dev/ttyUSB0")
        self.assertTrue(state["hardware"]["connected"])

    def test_live_refresh_shows_unverified_samples(self):
        self.station.sample(3700)
        state = self.state.refresh_live()
        self.assertEqual(state["chip_seq"], 0)
        self.assertEqual(state["pending"], 1)
        self.assertEqual(len(state["records"]), 1)
        self.assertEqual(state["voltage_mv"], 3700)
        self.assertEqual(state["health_status"], "unverified")
        self.assertIsNone(state["health"])

    def test_swap_accepts_real_signed_history(self):
        self.station.sample(3700)
        self.station.sample(2000)
        state = self.state.swap()
        self.assertEqual(state["last_result"]["status"], "accepted")
        self.assertEqual(state["last_result"]["code"], "VALID")
        self.assertEqual(state["last_seq"], 1)
        self.assertEqual(state["pending"], 0)
        self.assertEqual(state["health_status"], "trusted")
        self.assertEqual(state["health"]["samples"], 2)
        self.assertEqual(state["health"]["min_mv"], 2000)

    def test_delete_attack_is_detected(self):
        self.station.sample(3700)
        self.state.swap()
        self.station.sample(3700)
        self.state.refresh_live()
        result = self.state.attack_delete()
        self.assertTrue(result["ok"])
        state = self.state.swap()
        self.assertEqual(state["last_result"]["status"], "rejected")
        self.assertEqual(state["last_result"]["code"], "HISTORY_GAP")
        self.assertEqual(state["health_status"], "untrusted")
        self.assertEqual(state["fail_streak"], 1)

    def test_tamper_attack_is_detected(self):
        self.station.sample(3700)
        self.state.swap()
        self.station.sample(3700)
        self.state.refresh_live()
        self.assertTrue(self.state.attack_tamper()["ok"])
        state = self.state.swap()
        self.assertEqual(state["last_result"]["code"], "INVALID_HMAC")
        self.assertEqual(state["health_status"], "untrusted")

    def test_restore_clears_attack_and_verifies_again(self):
        self.station.sample(3700)
        self.state.swap()
        self.station.sample(3700)
        self.state.refresh_live()
        self.state.attack_delete()
        self.state.swap()
        self.assertEqual(self.state.state()["health_status"], "untrusted")

        state = self.state.restore()
        self.assertFalse(any(r["deleted"] for r in state["records"]))
        state = self.state.swap()
        self.assertEqual(state["last_result"]["status"], "accepted")
        self.assertEqual(state["health_status"], "trusted")
        self.assertEqual(state["fail_streak"], 0)

    def test_attack_requires_new_records(self):
        self.station.sample(3700)
        self.state.swap()
        result = self.state.attack_delete()
        self.assertFalse(result["ok"])
        self.assertNotIn("state", result)

    def test_three_failures_lock_then_unlock(self):
        self.station.sample(3700)
        self.state.swap()
        self.station.sample(3700)
        self.state.refresh_live()
        self.state.attack_tamper()
        self.assertEqual(self.state.swap()["fail_streak"], 1)
        self.assertEqual(self.state.swap()["fail_streak"], 2)
        state = self.state.swap()
        self.assertTrue(state["battery"]["locked"])
        self.assertTrue(state["last_result"].get("locked_now"))
        state = self.state.swap()
        self.assertEqual(state["last_result"]["code"], "BATTERY_LOCKED")
        state = self.state.unlock()
        self.assertFalse(state["battery"]["locked"])
        self.assertEqual(state["fail_streak"], 0)

    def test_full_buffer_reports_truncated(self):
        for _ in range(80):
            self.station.sample(3700)
        self.state.refresh_live()
        state = self.state.swap()
        self.assertEqual(state["last_result"]["status"], "accepted")
        self.assertEqual(state["last_result"]["code"], "HISTORY_TRUNCATED")
        self.assertEqual(len(state["records"]), 64)
        self.assertEqual(state["health"]["samples"], 64)
        self.assertEqual(state["chip_seq"], 79)

    def test_power_cycle_is_not_available_on_fpga(self):
        result = self.state.power_cycle()
        self.assertFalse(result["ok"])
        self.assertIn("Mode FPGA", result["message"])

    def test_reset_keeps_fpga_history(self):
        self.station.sample(3700)
        self.state.swap()
        state = self.state.reset()
        self.assertEqual(len(state["records"]), 1)
        self.assertEqual(state["last_result"], None)
        self.assertEqual(state["health_status"], "unverified")


if __name__ == "__main__":
    unittest.main()
