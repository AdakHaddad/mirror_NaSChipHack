"""
cocotb testbench for auth_ctrl.v.

Drives the UART RX pin with frames from model.protocol and checks every
response byte-for-byte against the Python HMAC reference:

  - AUTH_RESP signs the 0x41-prefixed message (spec section 6)
  - READ_HIST_RESP carries per-record 0x53 tags plus one 0x48 summary tag
    binding the nonce to the real oldest/last seq range
  - RESULT drives a fail counter that locks the chip after three failures
  - LOCK/UNLOCK flip the lock; a locked chip answers signed commands with
    CHIP_LOCKED (0x09)
  - STATUS replies with locked(1) | fail_cnt(1)

The ADS1115 is replaced by a simple adc_valid pulse; I2C timing is covered
by test_ads1115.py. The DUT samples every SAMPLE_CYCLES cycles and keeps a
64-record ring buffer of (seq, mv) with a tag per record.

The receiver is always started before the request is sent: a response can
begin while the last request bit is still on the wire.

Run: cd sim && make auth
"""

import struct

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import (
    ClockCycles,
    FallingEdge,
    RisingEdge,
    SimTimeoutError,
    with_timeout,
)
from cocotb.utils import get_sim_time

from model.hmac import hmac_sha256
from model.protocol import (
    AUTH_MSG_PREFIX,
    RECORD_MSG_PREFIX,
    SUMMARY_MSG_PREFIX,
    AuthStatus,
    Command,
    WireProtocol,
)

CLK_NS = 83               # ~12 MHz; the DUT only counts cycles
BIT_CYCLES = 12           # 12 MHz / 1 Mbaud (simulation only)
HALF_BIT = BIT_CYCLES // 2
BATTERY_ID = bytes.fromhex("42415401")
KEY = bytes(range(32))


def auth_msg(nonce, voltage):
    return (bytes([AUTH_MSG_PREFIX]) + nonce + BATTERY_ID
            + struct.pack(">H", voltage))


def record_msg(seq, mv):
    return (bytes([RECORD_MSG_PREFIX]) + BATTERY_ID
            + struct.pack(">IH", seq, mv))


def summary_msg(nonce, seq_oldest, seq_last):
    return (bytes([SUMMARY_MSG_PREFIX]) + nonce + BATTERY_ID
            + struct.pack(">II", seq_oldest, seq_last))


def frame(cmd, payload=b""):
    data = bytes([cmd]) + struct.pack(">H", len(payload)) + payload
    return data + bytes([WireProtocol._crc8(data)])


async def bring_up(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, unit="ns").start())
    dut.resetn.value = 0
    dut.rx.value = 1
    dut.adc_mv.value = 0
    dut.adc_valid.value = 0
    dut.adc_busy.value = 0
    dut.adc_error.value = 0
    dut.sw.value = 0
    dut.src_sel.value = 0
    await ClockCycles(dut.clk, 10)
    dut.resetn.value = 1
    await ClockCycles(dut.clk, 5)


async def adc_model(dut, state):
    """Answers conversions with a fixed (or ramp) millivolt value."""
    count = 0
    while True:
        await RisingEdge(dut.adc_start)
        if not state["enabled"]:
            continue
        if state.get("hold_until_tx"):
            # Finish this conversion only once the chip starts replying,
            # i.e. right after the READ_HIST snapshot.
            state["hold_until_tx"] = False
            await FallingEdge(dut.tx)
        await ClockCycles(dut.clk, 20)
        mv = (state["voltages"][count] if state["ramp"]
              else state["voltage"])
        dut.adc_mv.value = mv
        dut.adc_valid.value = 1
        state["mvs"].append(mv)
        state["count"] = count + 1
        count += 1
        await ClockCycles(dut.clk, 1)
        dut.adc_valid.value = 0
        if state["stop_after"] is not None and count >= state["stop_after"]:
            state["enabled"] = False


def adc_state(voltage=3300, stop_after=None, ramp=False):
    return {
        "voltage": voltage,
        "stop_after": stop_after,
        "ramp": ramp,
        "voltages": [3000 + (i * 37) % 900 for i in range(400)],
        "mvs": [],
        "count": 0,
        "enabled": True,
    }


async def uart_send_byte(dut, byte):
    dut.rx.value = 0
    await ClockCycles(dut.clk, BIT_CYCLES)
    for i in range(8):
        dut.rx.value = (byte >> i) & 1
        await ClockCycles(dut.clk, BIT_CYCLES)
    dut.rx.value = 1
    await ClockCycles(dut.clk, BIT_CYCLES)


async def uart_send_frame(dut, frame_bytes):
    for byte in frame_bytes:
        await uart_send_byte(dut, byte)


async def uart_recv_byte(dut):
    await FallingEdge(dut.tx)
    await ClockCycles(dut.clk, BIT_CYCLES + HALF_BIT)
    value = 0
    for i in range(8):
        value |= int(dut.tx.value) << i
        await ClockCycles(dut.clk, BIT_CYCLES)
    await ClockCycles(dut.clk, HALF_BIT)
    return value


async def uart_recv_frame(dut, length):
    data = bytearray()
    for _ in range(length):
        data.append(await with_timeout(uart_recv_byte(dut), 50, "ms"))
    return bytes(data)


async def exchange(dut, request, resp_len):
    """Listen first (the reply may start during the last request bit), send,
    then decode the response frame."""
    recv_task = cocotb.start_soon(uart_recv_frame(dut, resp_len))
    await uart_send_frame(dut, request)
    reply = await recv_task
    return WireProtocol.decode(reply)


async def expect_silence(dut, request):
    await uart_send_frame(dut, request)
    try:
        await with_timeout(FallingEdge(dut.tx), 2, "ms")
    except SimTimeoutError:
        return
    raise AssertionError("chip replied to an invalid request")


@cocotb.test()
async def test_auth_response_matches_python(dut):
    """AUTH_RESP signs the 0x41-prefixed message."""
    await bring_up(dut)
    cocotb.start_soon(adc_model(dut, adc_state(3300)))
    nonce = bytes(range(32))
    cmd, payload = await exchange(dut, frame(Command.AUTH_REQ, nonce), 42)
    assert cmd == Command.AUTH_RESP
    assert payload[:4] == BATTERY_ID
    voltage = struct.unpack(">H", payload[4:6])[0]
    assert voltage == 3300, voltage
    assert payload[6:38] == hmac_sha256(KEY, auth_msg(nonce, 3300))


@cocotb.test()
async def test_auth_second_nonce(dut):
    await bring_up(dut)
    cocotb.start_soon(adc_model(dut, adc_state(2000)))
    nonce = bytes([0xA5]) * 32
    cmd, payload = await exchange(dut, frame(Command.AUTH_REQ, nonce), 42)
    assert cmd == Command.AUTH_RESP
    voltage = struct.unpack(">H", payload[4:6])[0]
    assert voltage == 2000, voltage
    assert payload[6:38] == hmac_sha256(KEY, auth_msg(nonce, 2000))


@cocotb.test()
async def test_bad_crc_is_ignored(dut):
    await bring_up(dut)
    cocotb.start_soon(adc_model(dut, adc_state(3300)))
    bad = bytearray(frame(Command.AUTH_REQ, bytes(range(32))))
    bad[-1] ^= 0x01
    await expect_silence(dut, bytes(bad))
    assert (int(dut.led.value) & 0x8) != 0, "error LED did not light"


@cocotb.test()
async def test_unknown_command_is_ignored(dut):
    await bring_up(dut)
    cocotb.start_soon(adc_model(dut, adc_state(3300)))
    await expect_silence(dut, frame(0x42))
    assert (int(dut.led.value) & 0x8) != 0, "error LED did not light"


@cocotb.test()
async def test_status_reports_lock_state(dut):
    await bring_up(dut)
    cocotb.start_soon(adc_model(dut, adc_state(3300)))
    cmd, payload = await exchange(dut, frame(Command.STATUS), 6)
    assert cmd == Command.STATUS
    assert payload == bytes([0, 0]), payload.hex()

    await uart_send_frame(dut, frame(Command.LOCK))
    await ClockCycles(dut.clk, 20)
    cmd, payload = await exchange(dut, frame(Command.STATUS), 6)
    assert cmd == Command.STATUS
    assert payload == bytes([1, 0]), payload.hex()
    assert bool(int(dut.locked_flag.value))


@cocotb.test()
async def test_lock_replies_chip_locked(dut):
    await bring_up(dut)
    cocotb.start_soon(adc_model(dut, adc_state(3300)))
    await uart_send_frame(dut, frame(Command.LOCK))
    await ClockCycles(dut.clk, 20)

    nonce = bytes([0x5C]) * 32
    cmd, payload = await exchange(dut, frame(Command.AUTH_REQ, nonce), 8)
    assert cmd == Command.CHIP_LOCKED
    assert payload == BATTERY_ID

    cmd, payload = await exchange(dut, frame(Command.READ_HIST_REQ, nonce), 8)
    assert cmd == Command.CHIP_LOCKED
    assert payload == BATTERY_ID

    await uart_send_frame(dut, frame(Command.UNLOCK))
    await ClockCycles(dut.clk, 20)
    cmd, payload = await exchange(dut, frame(Command.AUTH_REQ, nonce), 42)
    assert cmd == Command.AUTH_RESP
    assert payload[6:38] == hmac_sha256(KEY, auth_msg(nonce, 3300))
    assert not bool(int(dut.locked_flag.value))


@cocotb.test()
async def test_fail_counter_locks_after_three_results(dut):
    await bring_up(dut)
    cocotb.start_soon(adc_model(dut, adc_state(3300)))

    for _ in range(2):
        await uart_send_frame(dut, frame(Command.RESULT,
                                         bytes([AuthStatus.INVALID_HMAC])))
        await ClockCycles(dut.clk, 40)
        assert not bool(int(dut.locked_flag.value))

    await uart_send_frame(dut, frame(Command.RESULT,
                                     bytes([AuthStatus.INVALID_HMAC])))
    await ClockCycles(dut.clk, 40)
    assert bool(int(dut.locked_flag.value))

    nonce = bytes([0x77]) * 32
    cmd, payload = await exchange(dut, frame(Command.AUTH_REQ, nonce), 8)
    assert cmd == Command.CHIP_LOCKED

    await uart_send_frame(dut, frame(Command.UNLOCK))
    await ClockCycles(dut.clk, 20)
    cmd, payload = await exchange(dut, frame(Command.STATUS), 6)
    assert payload == bytes([0, 0]), payload.hex()

    for _ in range(2):
        await uart_send_frame(dut, frame(Command.RESULT,
                                         bytes([AuthStatus.REPLAY_DETECTED])))
        await ClockCycles(dut.clk, 40)
    await uart_send_frame(dut, frame(Command.RESULT,
                                     bytes([AuthStatus.VALID])))
    await ClockCycles(dut.clk, 40)
    await uart_send_frame(dut, frame(Command.RESULT,
                                     bytes([AuthStatus.INVALID_HMAC])))
    await ClockCycles(dut.clk, 40)
    assert not bool(int(dut.locked_flag.value))


@cocotb.test()
async def test_leds_follow_last_verdict(dut):
    """Green after RESULT VALID, red after a rejected RESULT, and green again
    after the next RESULT VALID (the red flag must not stick)."""
    await bring_up(dut)
    cocotb.start_soon(adc_model(dut, adc_state(3300)))

    def leds():
        v = int(dut.led.value)
        return bool(v & 0x4), bool(v & 0x8)      # (green flag, red flag)

    nonce = bytes([0x66]) * 32
    cmd, _ = await exchange(dut, frame(Command.AUTH_REQ, nonce), 42)
    assert cmd == Command.AUTH_RESP
    await ClockCycles(dut.clk, 5)
    assert leds() == (False, False), f"reply alone is not a verdict: {leds()}"

    async def result(status):
        await uart_send_frame(dut, frame(Command.RESULT, bytes([status])))
        await ClockCycles(dut.clk, 40)

    await result(AuthStatus.VALID)
    assert leds() == (True, False), leds()
    await result(AuthStatus.INVALID_HMAC)
    assert leds() == (False, True), leds()
    await result(AuthStatus.VALID)
    assert leds() == (True, False), f"red stuck after valid: {leds()}"

    await uart_send_frame(dut, frame(Command.LOCK))
    await ClockCycles(dut.clk, 40)
    assert leds() == (False, True), leds()
    await uart_send_frame(dut, frame(Command.UNLOCK))
    await ClockCycles(dut.clk, 40)
    assert leds()[1] is False, f"red after unlock: {leds()}"


@cocotb.test()
async def test_periodic_sampling_interval(dut):
    """adc_start must fire every SAMPLE_CYCLES while the ADC is idle."""
    await bring_up(dut)
    cocotb.start_soon(adc_model(dut, adc_state(3300)))
    stamps = []
    for _ in range(3):
        await RisingEdge(dut.adc_start)
        stamps.append(get_sim_time(unit="ns"))
    expected = 12000 * CLK_NS
    for a, b in zip(stamps, stamps[1:]):
        delta = b - a
        assert abs(delta - expected) <= CLK_NS, (
            f"sample interval {delta} ns, expected ~{expected} ns"
        )


@cocotb.test()
async def test_read_hist_full_buffer_matches_python(dut):
    """65 records -> N=64, oldest=1; per-record 0x53 tags and one 0x48
    summary tag bound to the real seq range."""
    await bring_up(dut)
    state = adc_state(stop_after=65, ramp=True)
    cocotb.start_soon(adc_model(dut, state))

    while state["count"] < 65 or state["enabled"]:
        await ClockCycles(dut.clk, 500)
    await ClockCycles(dut.clk, 20)

    nonce = bytes([(i * 13 + 5) & 0xFF for i in range(32)])
    resp_len = 4 + 1 + 4 + 4 + 64 * 38 + 32
    cmd, payload = await exchange(dut, frame(Command.READ_HIST_REQ, nonce),
                                  resp_len)
    assert cmd == Command.READ_HIST_RESP
    assert len(payload) == 41 + 38 * 64

    n = payload[0]
    seq_oldest, seq_last = struct.unpack(">II", payload[1:9])
    assert n == 64, n
    assert seq_oldest == 1, seq_oldest
    assert seq_last == 64, seq_last

    for rec in range(n):
        off = 9 + 38 * rec
        seq, mv = struct.unpack(">IH", payload[off:off + 6])
        tag = payload[off + 6:off + 38]
        assert seq == seq_oldest + rec, (seq, seq_oldest + rec)
        assert mv == state["mvs"][seq], (seq, mv, state["mvs"][seq])
        assert tag == hmac_sha256(KEY, record_msg(seq, mv)), seq

    summary_tag = payload[9 + 38 * n:9 + 38 * n + 32]
    assert summary_tag == hmac_sha256(
        KEY, summary_msg(nonce, seq_oldest, seq_last))


def check_dump(payload, nonce):
    """Verifies a READ_HIST_RESP payload; returns (n, oldest, last, records)."""
    n = payload[0]
    seq_oldest, seq_last = struct.unpack(">II", payload[1:9])
    assert len(payload) == 41 + 38 * n
    records = []
    for rec in range(n):
        off = 9 + 38 * rec
        seq, mv = struct.unpack(">IH", payload[off:off + 6])
        tag = payload[off + 6:off + 38]
        assert seq == seq_oldest + rec, (seq, seq_oldest + rec)
        assert tag == hmac_sha256(KEY, record_msg(seq, mv)), seq
        records.append((seq, mv))
    if n:
        assert seq_last == seq_oldest + n - 1, (seq_oldest, seq_last, n)
    summary_tag = payload[9 + 38 * n:9 + 38 * n + 32]
    assert summary_tag == hmac_sha256(
        KEY, summary_msg(nonce, seq_oldest, seq_last))
    return n, seq_oldest, seq_last, records


@cocotb.test()
async def test_read_hist_full_buffer_while_sampling(dut):
    """A full buffer keeps sampling during the ~25 ms dump (1 sample/ms in
    simulation). A conversion is made to finish just as the reply starts, so
    the new sample would land in the slot of record 0 of the dump. The dump
    must still be the snapshot (record 0 intact, every tag valid), and the
    samples taken meanwhile are stored afterwards with contiguous seq."""
    await bring_up(dut)
    state = adc_state(ramp=True)
    cocotb.start_soon(adc_model(dut, state))

    while state["count"] < 70:
        await ClockCycles(dut.clk, 500)
    state["hold_until_tx"] = True
    await RisingEdge(dut.adc_start)

    nonce = bytes([(i * 7 + 3) & 0xFF for i in range(32)])
    resp_len = 4 + 1 + 4 + 4 + 64 * 38 + 32
    cmd, payload = await exchange(dut, frame(Command.READ_HIST_REQ, nonce),
                                  resp_len)
    assert cmd == Command.READ_HIST_RESP
    n, oldest, last, records = check_dump(payload, nonce)
    assert n == 64, n
    # Nothing was lost before the snapshot, so seq indexes the ADC trace.
    for seq, mv in records:
        assert mv == state["mvs"][seq], (seq, mv, state["mvs"][seq])

    # Let held samples drain and a few more arrive, then dump again.
    await ClockCycles(dut.clk, 12000 * 5)
    nonce2 = bytes([0x3C]) * 32
    cmd, payload = await exchange(dut, frame(Command.READ_HIST_REQ, nonce2),
                                  resp_len)
    assert cmd == Command.READ_HIST_RESP
    n2, oldest2, last2, _ = check_dump(payload, nonce2)
    assert n2 == 64, n2
    assert last2 > last, (last, last2)


@cocotb.test()
async def test_switch_source_without_adc(dut):
    """src_sel = 1 records 3000 + sw * 5 mV at every tick without starting
    the ADC, so the board can be tested with the ADS1115 disconnected."""
    await bring_up(dut)
    dut.sw.value = 140             # 3000 + 140 * 5 = 3700 mV
    dut.src_sel.value = 1
    starts = {"n": 0}

    async def count_starts():
        while True:
            await RisingEdge(dut.adc_start)
            starts["n"] += 1

    cocotb.start_soon(count_starts())
    await ClockCycles(dut.clk, 12000 * 4 + 200)

    nonce = bytes([0x11]) * 32
    cmd, payload = await exchange(dut, frame(Command.AUTH_REQ, nonce), 42)
    assert cmd == Command.AUTH_RESP
    assert struct.unpack(">H", payload[4:6])[0] == 3700
    assert payload[6:38] == hmac_sha256(KEY, auth_msg(nonce, 3700))

    nonce2 = bytes([0x22]) * 32
    recv = cocotb.start_soon(uart_recv_frame(dut, 4))
    await uart_send_frame(dut, frame(Command.READ_HIST_REQ, nonce2))
    head = await recv
    plen = (head[1] << 8) | head[2]
    n_rec = (plen - 41) // 38
    rest = await uart_recv_frame(dut, 4 + 38 * n_rec + 41 - 4)
    cmd, payload = WireProtocol.decode(head + rest)
    assert cmd == Command.READ_HIST_RESP
    n, _, _, records = check_dump(payload, nonce2)
    assert n >= 3, n
    assert all(mv == 3700 for _, mv in records), records
    assert starts["n"] == 0, f"ADC started {starts['n']} times"


@cocotb.test()
async def test_parser_recovers_after_bad_frames(dut):
    """A truncated frame and an oversized frame are dropped after the line
    idles; the next valid frame is answered."""
    await bring_up(dut)
    cocotb.start_soon(adc_model(dut, adc_state(3300)))
    timeout = 12_000_000 // 200 + 1000      # RX_TIMEOUT_CYCLES + margin

    # Truncated: CMD and half of LEN, then silence.
    for b in (0x01, 0x00):
        await uart_send_byte(dut, b)
    await ClockCycles(dut.clk, timeout)
    nonce = bytes([0x44]) * 32
    cmd, payload = await exchange(dut, frame(Command.AUTH_REQ, nonce), 42)
    assert cmd == Command.AUTH_RESP
    assert payload[6:38] == hmac_sha256(KEY, auth_msg(nonce, 3300))

    # Oversized: LEN = 256 followed by bytes that look like frames.
    junk = bytes([0x01, 0x01, 0x00]) + frame(Command.STATUS) * 8
    await uart_send_frame(dut, junk)
    await ClockCycles(dut.clk, timeout)
    nonce = bytes([0x55]) * 32
    cmd, payload = await exchange(dut, frame(Command.AUTH_REQ, nonce), 42)
    assert cmd == Command.AUTH_RESP
    assert payload[6:38] == hmac_sha256(KEY, auth_msg(nonce, 3300))
