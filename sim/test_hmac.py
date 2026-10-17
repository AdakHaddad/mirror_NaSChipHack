"""
cocotb testbench for hmac_sha256.v (AXI4-Lite interface)
Verifies against RFC 4231 test vectors + SeBatt protocol vectors.

Run: cd sim && make hmac
"""

import struct
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles, Timer


# AXI4-Lite register offsets
REG_CTRL    = 0x00
REG_STATUS  = 0x04
REG_MSG_LEN = 0x08
REG_KEY     = 0x10   # 0x10–0x2C (8 words)
REG_MSG     = 0x30   # 0x30–0x6C (16 words)
REG_HASH    = 0x70   # 0x70–0x8C (8 words)


async def reset_dut(dut):
    dut.s_axi_aresetn.value = 0
    dut.s_axi_awvalid.value = 0
    dut.s_axi_wvalid.value = 0
    dut.s_axi_bready.value = 1
    dut.s_axi_arvalid.value = 0
    dut.s_axi_rready.value = 1
    dut.s_axi_awaddr.value = 0
    dut.s_axi_wdata.value = 0
    dut.s_axi_araddr.value = 0
    dut.s_axi_awprot.value = 0
    dut.s_axi_arprot.value = 0
    dut.s_axi_wstrb.value = 0xF
    await ClockCycles(dut.s_axi_aclk, 10)
    dut.s_axi_aresetn.value = 1
    await ClockCycles(dut.s_axi_aclk, 5)


async def axi_write(dut, addr, data):
    """Single AXI4-Lite write transaction."""
    dut.s_axi_awaddr.value = addr
    dut.s_axi_awvalid.value = 1
    dut.s_axi_wdata.value = data
    dut.s_axi_wvalid.value = 1
    dut.s_axi_wstrb.value = 0xF

    # Wait for both ready
    for _ in range(20):
        await RisingEdge(dut.s_axi_aclk)
        if dut.s_axi_awready.value == 1 and dut.s_axi_wready.value == 1:
            break

    dut.s_axi_awvalid.value = 0
    dut.s_axi_wvalid.value = 0

    # Wait for bvalid
    for _ in range(20):
        await RisingEdge(dut.s_axi_aclk)
        if dut.s_axi_bvalid.value == 1:
            break
    await RisingEdge(dut.s_axi_aclk)


async def axi_read(dut, addr):
    """Single AXI4-Lite read transaction."""
    dut.s_axi_araddr.value = addr
    dut.s_axi_arvalid.value = 1

    for _ in range(20):
        await RisingEdge(dut.s_axi_aclk)
        if dut.s_axi_arready.value == 1:
            break

    dut.s_axi_arvalid.value = 0

    for _ in range(20):
        await RisingEdge(dut.s_axi_aclk)
        if dut.s_axi_rvalid.value == 1:
            val = int(dut.s_axi_rdata.value)
            return val

    raise TimeoutError("AXI read timeout")


async def write_key(dut, key_bytes):
    """Write 256-bit key (up to 32 bytes, zero-padded)."""
    key_padded = key_bytes.ljust(32, b'\x00')
    for i in range(8):
        word = struct.unpack('>I', key_padded[i*4:(i+1)*4])[0]
        await axi_write(dut, REG_KEY + i*4, word)


async def write_msg(dut, msg_bytes, msg_len=None):
    """Write message and set length."""
    if msg_len is None:
        msg_len = len(msg_bytes)
    # Pad to 64 bytes for register writes
    msg_padded = msg_bytes.ljust(64, b'\x00')
    await axi_write(dut, REG_MSG_LEN, msg_len)
    for i in range(16):
        word = struct.unpack('>I', msg_padded[i*4:(i+1)*4])[0]
        await axi_write(dut, REG_MSG + i*4, word)


async def start_and_wait(dut, timeout=2000):
    """Start HMAC computation, wait for done."""
    await axi_write(dut, REG_CTRL, 0x01)  # start

    for _ in range(timeout):
        await RisingEdge(dut.s_axi_aclk)
        status = await axi_read(dut, REG_STATUS)
        if status & 0x01:  # done bit
            return
    raise TimeoutError("HMAC did not complete")


async def read_hash(dut):
    """Read 256-bit HMAC result as hex string."""
    words = []
    for i in range(8):
        w = await axi_read(dut, REG_HASH + i*4)
        words.append(w)
    return ''.join(f'{w:08x}' for w in words)


@cocotb.test()
async def test_hmac_rfc4231_case1(dut):
    """RFC 4231 Test Case 1: key=0x0b*20, msg='Hi There'"""
    clock = Clock(dut.s_axi_aclk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    key = bytes.fromhex('0b' * 20)
    msg = b'Hi There'
    expected = 'b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7'

    await write_key(dut, key)
    await write_msg(dut, msg)
    await start_and_wait(dut)

    result = await read_hash(dut)
    dut._log.info(f"Got:      {result}")
    dut._log.info(f"Expected: {expected}")
    assert result == expected, f"HMAC mismatch"


@cocotb.test()
async def test_hmac_rfc4231_case2(dut):
    """RFC 4231 Test Case 2: key='Jefe', msg='what do ya want for nothing?'"""
    clock = Clock(dut.s_axi_aclk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    key = b'Jefe'
    msg = b'what do ya want for nothing?'
    expected = '5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843'

    await write_key(dut, key)
    await write_msg(dut, msg)
    await start_and_wait(dut)

    result = await read_hash(dut)
    dut._log.info(f"Got:      {result}")
    dut._log.info(f"Expected: {expected}")
    assert result == expected


@cocotb.test()
async def test_hmac_rfc4231_case3(dut):
    """RFC 4231 Test Case 3: key=0xaa*20, msg=0xdd*50"""
    clock = Clock(dut.s_axi_aclk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    key = bytes.fromhex('aa' * 20)
    msg = bytes.fromhex('dd' * 50)
    expected = '773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe'

    await write_key(dut, key)
    await write_msg(dut, msg)
    await start_and_wait(dut)

    result = await read_hash(dut)
    dut._log.info(f"Got:      {result}")
    dut._log.info(f"Expected: {expected}")
    assert result == expected


@cocotb.test()
async def test_hmac_sebatt_protocol(dut):
    """SeBatt protocol: key=bytes(range(32)), msg=nonce+id+voltage."""
    clock = Clock(dut.s_axi_aclk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await reset_dut(dut)

    # Match Python model defaults
    key = bytes(range(32))
    nonce = bytes(range(32))
    battery_id = b'BAT\x00'
    voltage = 3000
    voltage_bytes = struct.pack('>H', voltage)
    msg = nonce + battery_id + voltage_bytes  # 38 bytes

    # Compute expected with Python
    import hmac as hmac_mod
    import hashlib
    expected = hmac_mod.new(key, msg, hashlib.sha256).hexdigest()

    await write_key(dut, key)
    await write_msg(dut, msg, msg_len=38)
    await start_and_wait(dut)

    result = await read_hash(dut)
    dut._log.info(f"Got:      {result}")
    dut._log.info(f"Expected: {expected}")
    assert result == expected, f"SeBatt protocol HMAC mismatch"
