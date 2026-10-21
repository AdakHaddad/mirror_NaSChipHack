"""History verification tests for the Python reference and UART station."""

import os
from unittest.mock import patch

import pytest

from .protocol import (
    AuthRequest, AuthStatus, Command, HistoryDump, SeBattChip,
    Station as ModelStation, WireProtocol,
)
from .protocol import HistoryRecord
from .station import IdentityDB, PROFILES, Station as WireStation, health_card, health_summary
from .gen_vectors import sebatt_protocol_vectors


KEY = bytes(range(32))
BID = b'BAT\x01'


def _chip(count=5):
    chip = SeBattChip(BID, KEY, voltage_mv=3700)
    for i in range(count):
        chip.set_voltage(3600 + i)
        chip.sample_tick()
    return chip


def _nonce(tag=0):
    return bytes([(tag * 13 + i) & 0xFF for i in range(32)])


def _model_station():
    station = ModelStation()
    station.register_battery(BID, KEY)
    return station


def _wire_station(reply=b''):
    station = WireStation.__new__(WireStation)
    station.ser = FakeSerial(reply)
    station.db = IdentityDB()
    station.db.register(BID, KEY)
    station.log = []
    station.last_battery_id = None
    station.report_results = True
    station.profile = PROFILES["sel"]
    station._last_seen = None
    return station


class FakeSerial:
    """The canned reply arrives only after the first request is written, as
    on a real port (the station flushes its input before each request)."""

    def __init__(self, data):
        self.pending = bytearray(data)
        self.data = bytearray()
        self.timeout = None
        self.written = bytearray()
        self.is_open = True

    def read(self, size):
        out = bytes(self.data[:size])
        del self.data[:size]
        return out

    def reset_input_buffer(self):
        self.data.clear()

    def write(self, data):
        self.written.extend(data)
        self.data.extend(self.pending)
        self.pending.clear()

    def flush(self):
        pass

    def close(self):
        self.is_open = False


def test_protocol_vectors_cover_records_and_summary():
    vectors = sebatt_protocol_vectors()
    assert len(vectors) == 20
    for vector in vectors:
        assert bytes.fromhex(vector['record_msg_hex'])[0] == 0x53
        assert bytes.fromhex(vector['summary_msg_hex'])[0] == 0x48
        assert len(bytes.fromhex(vector['record_mac_hex'])) == 32
        assert len(bytes.fromhex(vector['summary_mac_hex'])) == 32


def test_valid_history_updates_anchor():
    chip = _chip(5)
    station = _model_station()
    nonce = _nonce(1)
    dump = chip.handle_read_hist_request(nonce)

    status = station.verify_history(AuthRequest(nonce), BID, dump)

    assert status == AuthStatus.VALID
    assert station.batteries[BID].seq_anchor == 4
    assert [r.seq for r in dump.records] == [0, 1, 2, 3, 4]


def test_truncated_history_is_accepted():
    chip = _chip(70)
    station = _model_station()
    nonce = _nonce(2)
    dump = chip.handle_read_hist_request(nonce)

    status = station.verify_history(AuthRequest(nonce), BID, dump)

    assert status == AuthStatus.HISTORY_TRUNCATED
    assert len(dump.records) == 64
    assert dump.seq_oldest == 6
    assert station.batteries[BID].seq_anchor == 69


def test_deleted_record_is_gap():
    chip = _chip(5)
    station = _model_station()
    nonce = _nonce(3)
    dump = chip.handle_read_hist_request(nonce)
    dump.records.pop(2)

    status = station.verify_history(AuthRequest(nonce), BID, dump)

    assert status == AuthStatus.HISTORY_GAP
    assert station.batteries[BID].seq_anchor == 0


def test_tampered_record_is_invalid_hmac():
    chip = _chip(5)
    station = _model_station()
    nonce = _nonce(4)
    dump = chip.handle_read_hist_request(nonce)
    dump.records[2].mv += 1

    status = station.verify_history(AuthRequest(nonce), BID, dump)

    assert status == AuthStatus.INVALID_HMAC
    assert station.batteries[BID].seq_anchor == 0


def test_tampered_summary_is_invalid_hmac():
    chip = _chip(5)
    station = _model_station()
    nonce = _nonce(5)
    dump = chip.handle_read_hist_request(nonce)
    dump.summary_tag = bytes([dump.summary_tag[0] ^ 1]) + dump.summary_tag[1:]

    status = station.verify_history(AuthRequest(nonce), BID, dump)

    assert status == AuthStatus.INVALID_HMAC


def test_rollback_after_power_cycle_is_rejected():
    station = _model_station()
    first_nonce = _nonce(6)
    first = _chip(5).handle_read_hist_request(first_nonce)
    assert station.verify_history(AuthRequest(first_nonce), BID, first) == AuthStatus.VALID

    rollback_nonce = _nonce(7)
    rollback = _chip(3).handle_read_hist_request(rollback_nonce)
    status = station.verify_history(AuthRequest(rollback_nonce), BID, rollback)

    assert status == AuthStatus.HISTORY_ROLLBACK
    assert station.batteries[BID].seq_anchor == 4


def test_empty_history_after_anchor_is_rollback():
    station = _model_station()
    first_nonce = _nonce(8)
    first = _chip(3).handle_read_hist_request(first_nonce)
    assert station.verify_history(AuthRequest(first_nonce), BID, first) == AuthStatus.VALID

    empty_nonce = _nonce(9)
    empty = SeBattChip(BID, KEY).handle_read_hist_request(empty_nonce)
    status = station.verify_history(AuthRequest(empty_nonce), BID, empty)

    assert status == AuthStatus.HISTORY_ROLLBACK
    assert station.batteries[BID].seq_anchor == 2


def test_empty_history_on_fresh_battery_is_valid():
    station = _model_station()
    nonce = _nonce(10)
    dump = SeBattChip(BID, KEY).handle_read_hist_request(nonce)

    status = station.verify_history(AuthRequest(nonce), BID, dump)

    assert status == AuthStatus.VALID
    assert station.batteries[BID].seq_anchor == 0


def test_replayed_history_nonce_is_rejected():
    chip = _chip(3)
    station = _model_station()
    nonce = _nonce(11)
    dump = chip.handle_read_hist_request(nonce)
    request = AuthRequest(nonce)

    assert station.verify_history(request, BID, dump) == AuthStatus.VALID
    assert station.verify_history(request, BID, dump) == AuthStatus.REPLAY_DETECTED


def test_wire_station_reads_and_verifies_history():
    chip = _chip(3)
    nonce = _nonce(12)
    dump = chip.handle_read_hist_request(nonce)
    station = _wire_station(WireProtocol.encode_read_hist_resp(dump))

    status, received = station.read_history(BID, nonce)

    assert status == AuthStatus.VALID
    assert received is not None
    assert [r.seq for r in received.records] == [0, 1, 2]


def test_wire_station_raw_history_does_not_verify():
    chip = _chip(3)
    nonce = _nonce(14)
    dump = chip.handle_read_hist_request(nonce)
    station = _wire_station(WireProtocol.encode_read_hist_resp(dump))

    status, sent_nonce, received = station.read_history_raw(BID, nonce)

    assert status == AuthStatus.VALID
    assert sent_nonce == nonce
    assert received is not None
    assert [r.seq for r in received.records] == [0, 1, 2]
    assert station.db.lookup(BID).seq_anchor == 0


def test_wire_station_auth_uses_0x41_prefix():
    nonce = _nonce(13)
    chip = _chip(1)
    response = chip.handle_auth_request(AuthRequest(nonce))
    station = _wire_station(WireProtocol.encode_auth_resp(response))

    with patch('model.station.os.urandom', return_value=nonce):
        status, voltage, battery_id = station.authenticate()

    assert status == AuthStatus.VALID
    assert voltage == 3600
    assert battery_id == BID.hex()


def _records(mvs, start=0):
    return [HistoryRecord(seq=start + i, mv=mv, tag=b'') for i, mv in enumerate(mvs)]


def test_health_card_counts_deep_discharge_events():
    # sel profile: pin x 4200/3300, deep below 2.5 V cell (about 1964 mV pin)
    lines = health_card(_records([3000, 1500, 1400, 3000, 1800, 3000]), PROFILES["sel"])
    assert "terendah 1,78 V pada seq 2" in lines[0]
    assert "terkuras dalam 2 kali" in lines[1]


def test_health_summary_counts_a_charge_cycle():
    # 3,82 V -> 2,04 V (below 3,0 V) -> 4,07 V (above 4,0 V) = one cycle
    h = health_summary(_records([3000, 1600, 3200]), PROFILES["sel"])
    assert h["cycles"] == 1 and h["deep_events"] == 1


def test_health_card_aki12v_profile():
    # 47k/10k divider: 2210 mV pin = 12,6 V, 1800 mV pin = 10,26 V (< 10,5 V)
    lines = health_card(_records([2210, 1800]), PROFILES["aki12v"])
    assert "terendah 10,26 V" in lines[0]
    assert "terkuras dalam 1 kali" in lines[1]


def test_health_card_lipo3s_profile():
    # 120k/10k/15k divider, x5.8: 2172 mV pin = 12,60 V (knob top),
    # 1500 mV pin = 8,70 V (< 9,0 V), 1800 mV pin = 10,44 V (< 10,5 V arms).
    lines = health_card(_records([2172, 1500, 1800, 2172]), PROFILES["lipo3s"])
    assert "terendah 8,70 V" in lines[0]
    assert "siklus 1" in lines[0]
    assert "terkuras dalam 1 kali" in lines[1]


def test_history_report_hides_health_when_rejected():
    station = _wire_station()
    dump = HistoryDump(battery_id=BID, seq_oldest=0, seq_last=1,
                       records=_records([500, 3000]), summary_tag=b'')
    text = " ".join(station.history_report(AuthStatus.HISTORY_GAP, dump))
    assert "DITOLAK" in text and "TIDAK DAPAT DIPERCAYA" in text
    assert "Kesehatan" not in text


def test_history_report_warns_when_sampling_stops():
    station = _wire_station()
    dump = HistoryDump(battery_id=BID, seq_oldest=0, seq_last=4,
                       records=_records([3000] * 5), summary_tag=b'')
    with patch('model.station.time.monotonic', return_value=100.0):
        first = " ".join(station.history_report(AuthStatus.VALID, dump))
    with patch('model.station.time.monotonic', return_value=105.0):
        later = " ".join(station.history_report(AuthStatus.VALID, dump))
    assert "PERINGATAN" not in first
    assert "PERINGATAN" in later and "5 s" in later
