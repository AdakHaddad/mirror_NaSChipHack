import unittest

from web.demo import BUFFER_SIZE, DemoState


class DemoStateTests(unittest.TestCase):
    def setUp(self):
        self.demo = DemoState()

    def test_initial_state(self):
        state = self.demo.state()
        self.assertEqual(state["chip_seq"], 16)
        self.assertEqual(state["last_seq"], 0)
        self.assertEqual(state["pending"], 16)
        self.assertEqual(len(state["records"]), 16)
        self.assertEqual(state["health_status"], "unverified")
        self.assertIsNone(state["health"])
        self.assertIsNone(state["last_result"])

    def test_initial_swap_is_accepted(self):
        state = self.demo.swap()
        self.assertEqual(state["last_result"]["status"], "accepted")
        self.assertEqual(state["last_result"]["code"], "VALID")
        self.assertEqual(state["last_seq"], 16)
        self.assertEqual(state["pending"], 0)
        self.assertEqual(state["health_status"], "trusted")
        self.assertIsNotNone(state["health"])
        self.assertEqual(state["health"]["samples"], 16)
        self.assertEqual(state["fail_streak"], 0)

    def test_deep_discharge_updates_health(self):
        self.demo.swap()
        self.demo.record(2000)
        state = self.demo.swap()
        self.assertEqual(state["last_result"]["status"], "accepted")
        self.assertEqual(state["health"]["deep"], 1)
        self.assertEqual(state["health"]["min_mv"], 2000)
        self.assertEqual(state["health"]["samples"], 17)

    def test_charge_cycle_is_counted(self):
        self.demo.swap()
        self.demo.record(2000)
        self.demo.swap()
        self.demo.record(4160)
        state = self.demo.swap()
        self.assertEqual(state["last_result"]["status"], "accepted")
        self.assertEqual(state["health"]["cycles"], 1)

    def test_deleted_record_is_rejected(self):
        self.demo.swap()
        self.demo.record(3700)
        self.assertTrue(self.demo.attack_delete()["ok"])
        state = self.demo.swap()
        self.assertEqual(state["last_result"]["status"], "rejected")
        self.assertEqual(state["last_result"]["code"], "HISTORY_GAP")
        self.assertEqual(state["fail_streak"], 1)
        self.assertEqual(state["health_status"], "untrusted")
        self.assertIsNone(state["health"])

    def test_tampered_record_is_rejected(self):
        self.demo.swap()
        self.demo.record(3700)
        self.assertTrue(self.demo.attack_tamper()["ok"])
        state = self.demo.swap()
        self.assertEqual(state["last_result"]["status"], "rejected")
        self.assertEqual(state["last_result"]["code"], "INVALID_HMAC")
        self.assertIn("diubah", state["last_result"]["message"])
        self.assertEqual(state["fail_streak"], 1)

    def test_restore_then_swap_is_accepted(self):
        self.demo.swap()
        self.demo.record(3700)
        self.demo.attack_delete()
        self.demo.swap()
        self.assertEqual(self.demo.state()["health_status"], "untrusted")
        state = self.demo.restore()
        self.assertEqual(state["health_status"], "unverified")
        state = self.demo.swap()
        self.assertEqual(state["last_result"]["status"], "accepted")
        self.assertEqual(state["health_status"], "trusted")
        self.assertEqual(state["fail_streak"], 0)

    def test_power_cycle_causes_rollback(self):
        self.demo.swap()
        state = self.demo.power_cycle()
        self.assertEqual(state["records"], [])
        self.assertEqual(state["chip_seq"], 0)
        self.assertTrue(state["power_cycled"])
        state = self.demo.swap()
        self.assertEqual(state["last_result"]["status"], "rejected")
        self.assertEqual(state["last_result"]["code"], "ROLLBACK")

    def test_three_failures_lock_chip(self):
        self.demo.swap()
        self.demo.record(3700)
        self.assertTrue(self.demo.attack_tamper()["ok"])
        self.assertEqual(self.demo.swap()["fail_streak"], 1)
        self.assertEqual(self.demo.swap()["fail_streak"], 2)
        state = self.demo.swap()
        self.assertEqual(state["last_result"]["code"], "INVALID_HMAC")
        self.assertTrue(state["battery"]["locked"])
        self.assertTrue(state["last_result"].get("locked_now"))
        self.assertIn("terkunci", state["last_result"]["message"])

        state = self.demo.swap()
        self.assertEqual(state["last_result"]["code"], "BATTERY_LOCKED")
        self.assertTrue(state["battery"]["locked"])

        state = self.demo.unlock()
        self.assertFalse(state["battery"]["locked"])
        self.assertEqual(state["fail_streak"], 0)

    def test_restore_resets_fail_streak(self):
        self.demo.swap()
        self.demo.record(3700)
        self.demo.attack_tamper()
        self.demo.swap()
        self.assertEqual(self.demo.state()["fail_streak"], 1)
        state = self.demo.restore()
        self.assertEqual(state["fail_streak"], 0)

    def test_attack_requires_new_records(self):
        first = self.demo.attack_delete()
        second = self.demo.attack_tamper()
        self.assertFalse(first["ok"])
        self.assertFalse(second["ok"])
        self.assertNotIn("state", first)
        self.assertNotIn("state", second)

    def test_buffer_drops_oldest_records(self):
        for _ in range(60):
            self.demo.record(3700)
        state = self.demo.state()
        self.assertEqual(len(state["records"]), BUFFER_SIZE)
        self.assertEqual(state["records"][0]["seq"], 13)
        self.assertEqual(state["records"][-1]["seq"], 76)
        self.assertEqual(state["chip_seq"], 76)


if __name__ == "__main__":
    unittest.main()
