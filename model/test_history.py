"""History verification tests for the Python reference and UART station."""

import os
from unittest.mock import patch

import pytest

from .protocol import (
    AuthRequest, AuthStatus, Command, HistoryDump, SeBattChip,
    Station as ModelStation, WireProtocol,
)
from .station import IdentityDB, Station as WireStation
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
