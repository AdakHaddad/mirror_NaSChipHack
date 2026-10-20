"""
cocotb testbench for auth_ctrl.v.

Drives the UART RX pin with frames from model.protocol and checks the
AUTH_RESP frame byte-for-byte against the Python HMAC reference.

The ADS1115 is replaced by a simple adc_valid pulse; the I2C timing is covered
by test_ads1115.py.

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

from model.hmac import hmac_sha256
from model.protocol import (
    AuthRequest,
    Command,
    WireProtocol,
)

CLK_NS = 83               # ~12 MHz; the DUT only counts cycles
BIT_CYCLES = 104          # 12 MHz / 115200
HALF_BIT = BIT_CYCLES // 2
BATTERY_ID = bytes.fromhex("42415401")
KEY = bytes(range(32))


async def bring_up(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, unit="ns").start())
    dut.resetn.value = 0
    dut.rx.value = 1
    dut.adc_mv.value = 0
    dut.adc_valid.value = 0
    dut.adc_busy.value = 0
    dut.adc_error.value = 0
    await ClockCycles(dut.clk, 10)
    dut.resetn.value = 1
    await ClockCycles(dut.clk, 5)


async def adc_model(dut, state):
    while True:
        await RisingEdge(dut.adc_start)
        await ClockCycles(dut.clk, 20)
        dut.adc_mv.value = state["voltage"]
        dut.adc_valid.value = 1
        await ClockCycles(dut.clk, 1)
        dut.adc_valid.value = 0


async def uart_send_byte(dut, byte):
    dut.rx.value = 0
    await ClockCycles(dut.clk, BIT_CYCLES)
    for i in range(8):
        dut.rx.value = (byte >> i) & 1
        await ClockCycles(dut.clk, BIT_CYCLES)
    dut.rx.value = 1
    await ClockCycles(dut.clk, BIT_CYCLES)


async def uart_send_frame(dut, frame):
    for byte in frame:
        await uart_send_byte(dut, byte)


async def uart_recv_byte(dut):
    await FallingEdge(dut.tx)
    await ClockCycles(dut.clk, BIT_CYCLES + HALF_BIT)
    value = 0
    for i in range(8):
        value |= int(dut.tx.value) << i
        await ClockCycles(dut.clk, BIT_CYCLES)
    # We are at the middle of the stop bit. Return before the next start
    # edge so the next call can catch it.
    await ClockCycles(dut.clk, HALF_BIT)
    return value


async def uart_recv_frame(dut, length):
    frame = bytearray()
    for _ in range(length):
        frame.append(await with_timeout(uart_recv_byte(dut), 2, "ms"))
    return bytes(frame)


async def auth_roundtrip(dut, nonce, voltage):
    state = {"voltage": voltage}
    cocotb.start_soon(adc_model(dut, state))

    await uart_send_frame(dut, WireProtocol.encode_auth_req(AuthRequest(nonce)))
    response = await uart_recv_frame(dut, 42)

    cmd, payload = WireProtocol.decode(response)
    assert cmd == Command.AUTH_RESP
    resp = WireProtocol.decode_auth_resp(payload)
    expected_msg = nonce + BATTERY_ID + struct.pack(">H", voltage)
    expected_hmac = hmac_sha256(KEY, expected_msg)

    assert resp.battery_id == BATTERY_ID, resp.battery_id.hex()
    assert resp.voltage == voltage, resp.voltage
    assert resp.hmac_resp == expected_hmac, "HMAC mismatch"


@cocotb.test()
async def test_auth_response_matches_python(dut):
    await bring_up(dut)
    await auth_roundtrip(dut, bytes(range(32)), 3300)


@cocotb.test()
async def test_auth_second_nonce(dut):
    await bring_up(dut)
    await auth_roundtrip(dut, bytes([0xA5]) * 32, 2000)


@cocotb.test()
async def test_bad_crc_is_ignored(dut):
    await bring_up(dut)
    cocotb.start_soon(adc_model(dut, {"voltage": 3300}))

    frame = bytearray(WireProtocol.encode_auth_req(AuthRequest(bytes(range(32)))))
    frame[-1] ^= 0x01
    await uart_send_frame(dut, frame)

    try:
        await with_timeout(FallingEdge(dut.tx), 2, "ms")
        assert False, "chip replied to a frame with a bad CRC"
    except SimTimeoutError:
        pass

    assert (int(dut.led.value) & 0x8) != 0, "error LED did not light"


@cocotb.test()
async def test_unknown_command_is_ignored(dut):
    await bring_up(dut)
    cocotb.start_soon(adc_model(dut, {"voltage": 3300}))

    await uart_send_frame(dut, WireProtocol._frame(Command.STATUS, b""))

    try:
        await with_timeout(FallingEdge(dut.tx), 2, "ms")
        assert False, "chip replied to an unsupported command"
    except SimTimeoutError:
        pass

    assert (int(dut.led.value) & 0x8) != 0, "error LED did not light"
