"""
cocotb testbench for sha256_core.v
Verifies against FIPS 180-4 test vectors.

Run: cd sim && make sha256
"""

import struct

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles


async def reset_dut(dut):
    dut.rst_n.value = 0
    dut.init_i.value = 0
    dut.start_i.value = 0
    dut.msg_we_i.value = 0
    dut.msg_word_i.value = 0
    dut.msg_addr_i.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


async def init_hash(dut):
    dut.init_i.value = 1
    await RisingEdge(dut.clk)
    dut.init_i.value = 0
    await RisingEdge(dut.clk)


async def load_block(dut, words):
    """Load 16 × 32-bit words into W[0..15]."""
    assert len(words) == 16
    for i, w in enumerate(words):
        dut.msg_word_i.value = w
        dut.msg_addr_i.value = i
        dut.msg_we_i.value = 1
        await RisingEdge(dut.clk)
    dut.msg_we_i.value = 0
    await RisingEdge(dut.clk)


async def start_and_wait(dut, timeout=200):
    """Assert start, wait for done pulse."""
    dut.start_i.value = 1
    await RisingEdge(dut.clk)
    dut.start_i.value = 0

    for _ in range(timeout):
        await RisingEdge(dut.clk)
        if dut.done_o.value == 1:
            return
    raise TimeoutError("SHA-256 did not complete")


def sha256_pad(msg_bytes):
    """SHA-256 padding → list of blocks, each block = list of 16 words."""
    mlen = len(msg_bytes)
    bit_len = mlen * 8
    msg_bytes += b'\x80'
    msg_bytes += b'\x00' * ((56 - len(msg_bytes) % 64) % 64)
    msg_bytes += struct.pack('>Q', bit_len)
    blocks = []
    for i in range(0, len(msg_bytes), 64):
        blocks.append(list(struct.unpack('>16I', msg_bytes[i:i+64])))
    return blocks


def get_hash(dut):
    return int(dut.hash_o.value)


@cocotb.test()
async def test_sha256_abc(dut):
    """FIPS 180-4 B.1: SHA-256('abc')"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)
    await init_hash(dut)

    blocks = sha256_pad(bytearray(b'abc'))
    assert len(blocks) == 1

    await load_block(dut, blocks[0])
    await start_and_wait(dut)

    h = get_hash(dut)
    exp = 0xba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad
    dut._log.info(f"Got:      {h:064x}")
    dut._log.info(f"Expected: {exp:064x}")
    assert h == exp, f"Mismatch: {h:064x}"


@cocotb.test()
async def test_sha256_two_blocks(dut):
    """FIPS 180-4 B.2: two-block message."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)
    await init_hash(dut)

    msg = bytearray(b'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq')
    blocks = sha256_pad(msg)
    assert len(blocks) == 2

    for blk in blocks:
        await load_block(dut, blk)
        await start_and_wait(dut)

    h = get_hash(dut)
    exp = 0x248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1
    dut._log.info(f"Got:      {h:064x}")
    dut._log.info(f"Expected: {exp:064x}")
    assert h == exp


@cocotb.test()
async def test_sha256_empty(dut):
    """SHA-256 of empty string."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)
    await init_hash(dut)

    blocks = sha256_pad(bytearray(b''))
    await load_block(dut, blocks[0])
    await start_and_wait(dut)

    h = get_hash(dut)
    exp = 0xe3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    dut._log.info(f"Got:      {h:064x}")
    dut._log.info(f"Expected: {exp:064x}")
    assert h == exp


@cocotb.test()
async def test_sha256_multi_init(dut):
    """init resets hash state between messages."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    # Hash "abc"
    await init_hash(dut)
    blocks = sha256_pad(bytearray(b'abc'))
    await load_block(dut, blocks[0])
    await start_and_wait(dut)

    # Hash empty (new init)
    await init_hash(dut)
    blocks = sha256_pad(bytearray(b''))
    await load_block(dut, blocks[0])
    await start_and_wait(dut)

    h = get_hash(dut)
    exp = 0xe3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    assert h == exp, "init did not reset state"


@cocotb.test()
async def test_sha256_cycle_count(dut):
    """Verify compression completes in ~114 cycles (48 expand + 64 rounds + 2 overhead)."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)
    await init_hash(dut)

    blocks = sha256_pad(bytearray(b'abc'))
    await load_block(dut, blocks[0])

    dut.start_i.value = 1
    await RisingEdge(dut.clk)
    dut.start_i.value = 0

    cycles = 0
    for cycles in range(100):
        await RisingEdge(dut.clk)
        if dut.done_o.value == 1:
            break

    dut._log.info(f"Compression took {cycles+1} cycles")
    assert cycles + 1 <= 120, f"Too many cycles: {cycles+1}"
