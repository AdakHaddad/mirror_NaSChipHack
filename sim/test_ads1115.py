"""
cocotb testbench for i2c_master.v + ads1115_ctrl.v.

The model below is a transaction-level ADS1115: it acknowledges the address and
register pointer, accepts the 0xC383 config write, and returns a 16-bit
conversion value on the repeated-start read. Run:

    cd sim && make ads1115
"""

import cocotb
from cocotb.clock import Clock
from cocotb.handle import Force, Release
from cocotb.triggers import (
    ClockCycles,
    FallingEdge,
    RisingEdge,
    with_timeout,
)

CONFIG_REG = 0x01
CONV_REG = 0x00
CONFIG_VALUE = 0xC383


async def wait_start(dut):
    """Wait for START, then for SCL to fall before the first address bit."""
    while True:
        await FallingEdge(dut.sda)
        if int(dut.scl.value) == 1:
            await FallingEdge(dut.scl)
            return


async def wait_stop(dut):
    """Wait until SDA rises while SCL is high."""
    while True:
        await RisingEdge(dut.sda)
        if int(dut.scl.value) == 1:
            return


async def recv_byte(dut):
    value = 0
    for _ in range(8):
        await RisingEdge(dut.scl)
        value = (value << 1) | int(dut.sda.value)
    return value


async def send_ack(dut):
    """Pull SDA low for the 9th clock."""
    await FallingEdge(dut.scl)
    dut.sda.value = Force(0)
    await RisingEdge(dut.scl)
    await FallingEdge(dut.scl)
    dut.sda.value = Release()


async def send_byte(dut, value):
    """Shift out one byte, then wait for the master's ACK/NACK clock."""
    for i in range(8):
        bit = (value >> (7 - i)) & 1
        if bit == 0:
            dut.sda.value = Force(0)
        else:
            dut.sda.value = Release()
        await RisingEdge(dut.scl)
        await FallingEdge(dut.scl)

    # Release only after the 8th falling edge, so the master samples the
    # last data bit correctly before its ACK/NACK clock.
    dut.sda.value = Release()
    await RisingEdge(dut.scl)
    await FallingEdge(dut.scl)


async def ads1115_model(dut, state):
    """Deterministic model matching ads1115_ctrl's transaction sequence."""
    while True:
        await wait_start(dut)
        addr = await recv_byte(dut)
        if addr != 0x90:
            state["errors"].append(f"write address 0x{addr:02x} != 0x90")
        await send_ack(dut)

        reg = await recv_byte(dut)
        await send_ack(dut)

        if reg == CONFIG_REG:
            hi = await recv_byte(dut)
            await send_ack(dut)
            lo = await recv_byte(dut)
            await send_ack(dut)
            state["config"] = (hi << 8) | lo
            await wait_stop(dut)

        elif reg == CONV_REG:
            # Repeated start, then read address.
            await wait_start(dut)
            addr = await recv_byte(dut)
            if addr != 0x91:
                state["errors"].append(f"read address 0x{addr:02x} != 0x91")
            await send_ack(dut)

            value = state["voltage"] & 0xFFFF
            await send_byte(dut, value >> 8)
            await send_byte(dut, value & 0xFF)
            await wait_stop(dut)

        else:
            state["errors"].append(f"unexpected register 0x{reg:02x}")
            await wait_stop(dut)


async def pulse_start(dut):
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0


async def wait_valid(dut):
    await with_timeout(RisingEdge(dut.valid), 5, "ms")


async def bring_up(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    dut.resetn.value = 0
    dut.start.value = 0
    await ClockCycles(dut.clk, 10)
    dut.resetn.value = 1
    await ClockCycles(dut.clk, 5)


@cocotb.test()
async def test_ads1115_single_shot(dut):
    """Two single-shot conversions at different pot voltages."""
    await bring_up(dut)

    state = {"voltage": 26400, "config": None, "errors": []}
    cocotb.start_soon(ads1115_model(dut, state))

    await pulse_start(dut)
    await wait_valid(dut)

    assert state["config"] == CONFIG_VALUE, (
        f"config 0x{state['config']:04x} != 0x{CONFIG_VALUE:04x}"
    )
    assert int(dut.raw.value) == 26400
    assert int(dut.mv.value) == 3300
    assert not state["errors"], state["errors"]

    # Second sample: 2.000 V.
    state["voltage"] = 16000
    await pulse_start(dut)
    await wait_valid(dut)

    assert int(dut.raw.value) == 16000
    assert int(dut.mv.value) == 2000
    assert not state["errors"], state["errors"]


@cocotb.test()
async def test_ads1115_rejects_negative_raw(dut):
    """A differential-style negative code is clamped to 0 mV."""
    await bring_up(dut)

    state = {"voltage": 0x8000, "config": None, "errors": []}
    cocotb.start_soon(ads1115_model(dut, state))

    await pulse_start(dut)
    await wait_valid(dut)

    assert int(dut.raw.value) == 0x8000
    assert int(dut.mv.value) == 0
    assert not state["errors"], state["errors"]


async def expect_error_without_sample(dut):
    """A start on a stuck bus must end in error, not in a valid 0 mV sample."""
    valid_seen = {"v": False}

    async def watch_valid():
        while True:
            await RisingEdge(dut.valid)
            valid_seen["v"] = True

    cocotb.start_soon(watch_valid())
    await pulse_start(dut)
    for _ in range(2000):
        await RisingEdge(dut.clk)
        if int(dut.error.value) == 1 and int(dut.busy.value) == 0:
            break
    assert int(dut.error.value) == 1, "stuck bus was not reported"
    await ClockCycles(dut.clk, 200)
    assert not valid_seen["v"], "a sample was produced from a stuck bus"


@cocotb.test()
async def test_ads1115_sda_stuck_low_is_error(dut):
    """SDA shorted to GND (Pmod 2 to GND) used to read as ACK + 0x0000."""
    await bring_up(dut)
    dut.sda.value = Force(0)
    await ClockCycles(dut.clk, 5)
    await expect_error_without_sample(dut)
    dut.sda.value = Release()


@cocotb.test()
async def test_ads1115_scl_stuck_low_is_error(dut):
    await bring_up(dut)
    dut.scl.value = Force(0)
    await ClockCycles(dut.clk, 5)
    await expect_error_without_sample(dut)
    dut.scl.value = Release()
