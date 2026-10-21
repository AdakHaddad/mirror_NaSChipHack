# SeBatt — Complete Project Context

> Concept, code, protocol, hardware, and demo in one document.
>
> Written 19 October 2026; updated 21 October 2026 after the signed-history
> implementation. Python model 52/52 tests pass, RTL simulation 23/23 tests pass
> (sha256 + hmac + ads1115 + auth/history; see Section 6.3), offline station demo
> passes.
> Hardware results are marked separately.
>
> **Update 21 Oct 2026 (KV260):** Pmod pin map, PS clock-only block design, full
> bitstream and `.bit.bin` are rebuilt after the `sg_req*`, dump-race, CRC, and
> parser-resync fixes (WNS +1.466 ns, 5 633 LUT / 6 201 FF); physical KV260
> tests are still pending.
>
> **Revision 19 Oct 2026 (hardware session):** the demo ADC changed from an
> SPI MCP3202 to an **ADS1115 over I2C** (no SPI ADC available). Practice board
> is the **Cmod S7**; demo-day board remains the **Kria KV260**. The Flow A
> Basys 3 / MicroBlaze path is kept only as a fallback and video source.

This file is the "master map". The formal narrative lives in
[`docs/catatan-teknis/alur-teknis.md`](docs/catatan-teknis/alur-teknis.md) and
[`docs/catatan-teknis/alur-demo.md`](docs/catatan-teknis/alur-demo.md); the
test procedure lives in
[`docs/catatan-teknis/rencana-tes-basys3.md`](docs/catatan-teknis/rencana-tes-basys3.md).

---

## 0. How to use this document

Read in this order to master the project:

1. **Sections 1–3** — the idea, the threat model, and the cryptography. If you
   can explain these without notes, you can answer most judge questions.
2. **Sections 4–5** — the wire protocol and repository map. This is the contract
   between RTL, Python, and firmware.
3. **Section 6** — file-by-file code walkthrough. Read the Python side first,
   then the RTL. The Python model is the golden reference; the RTL must match it.
4. **Sections 7–8** — how the pieces connect and how to run every test.
5. **Sections 9–10** — board bring-up and the live demo script.
6. **Sections 11–12** — honest status, known gaps, and what to build next.

The one-sentence version:

> SeBatt is a chip inside an EV battery pack that signs the battery's voltage
> history at the point of measurement, so a swap station can prove that the
> history was not edited, deleted, replayed, or rolled back.

---

## 1. The idea in one page

### 1.1 The real problem

A battery swap station sees only two things when a pack arrives:

- the pack's identity (QR code, serial number, or a challenge-response chip), and
- the voltage **right now**.

It does **not** see what happened during the previous week. A pack that was
drained to 2.0 V, left empty, or overcharged may look perfectly normal at 4.2 V
after a recharge. The damage is permanent, but the evidence is gone.

Today the history is reported by BMS firmware. That firmware is software: it can
be reflashed, patched, or replaced by a proxy board sitting between the battery
and the station. The owner of the battery has an incentive to hide abuse when
selling the pack, claiming warranty, or returning a rented battery.

Existing commercial chips do not solve this:

| Chip | What it does | What it does **not** do |
|---|---|---|
| TI BQ40Z50 | Measures voltage/current, stores a lifetime log, SHA-1 authentication | The log is plain data in flash, unsigned, no sequence number, writable through data-flash access. SHA-1 authenticates the **pack identity** to the host, not the history |
| ADI MAX17205 | SHA-256 authentication, history log | Still anti-cloning of the pack, not integrity of the recorded history |
| Secure elements (e.g. DS28E38) | PUF-based identity | Data comes from an external MCU; the sensor data can be spoofed before it reaches the secure element |

The gap is **signed sensor history**, not another identity chip.

### 1.2 The insight

Move the trust boundary to the measurement point:

- The ADC and the signing engine are in the same chip.
- Every sample is numbered with a counter that can only increase.
- Every sample is signed immediately with HMAC-SHA-256.
- The station verifies the signatures and the sequence, not the BMS's story.

The BMS may still modify or delete data **after** it leaves the chip. That is
exactly the attack being demonstrated. It cannot produce a valid signature for
modified data, and it cannot fill a sequence gap.

### 1.3 The solution

```
voltage source → ADC → sample + seq → HMAC-SHA-256 → ring buffer (64 records)
                                                          │
station nonce ────────────────────────────────────────────┤
                                                          ▼
                         UART → station: records + tags → verify HMAC + sequence
                                                          │
                                              ACCEPT / REJECT + health card
```

Two independent mechanisms:

1. **Authenticity** — HMAC over `ID ‖ seq ‖ voltage` with key `K`.
2. **Freshness and completeness** — a monotonic `seq` plus a station-side
   anchor `last_seq`, and a fresh nonce for every authentication.

### 1.4 What is actually novel

Not SHA-256. Not HMAC. Not a PUF. The novel part is the **combination and
placement**:

- signing happens at the sensor, inside the same die as the ADC (target),
- the history itself is signed, not just the pack identity,
- sequence numbers make deletion and rollback detectable,
- the verifier keeps only a small anchor per battery, not the full history.

### 1.5 Threat model

**In scope**

| Attacker capability | Example | Detection |
|---|---|---|
| Modify a record in transit | Proxy changes 2.0 V to 3.6 V | HMAC mismatch |
| Delete records | Proxy drops the over-discharge samples | Sequence gap |
| Replay an old response | Re-send last week's valid exchange | Nonce reuse |
| Roll back the counter | Cut power so `seq` returns to 0 | `last_seq` regression |
| Swap a pack's identity | Use a stolen/recalled pack | DB lock / unknown ID |
| Repeated failed attempts | Brute-force attempts | Chip locks after 3 failures (target) |

**Out of scope / accepted limitations**

- **ADC outside the chip in the demo.** The ADS1115 (I2C) is a separate module,
  so the voltage can be spoofed before it enters the FPGA. The final product
  puts the ADC on the same die.
- **Volatile history and counter.** FPGA BRAM loses state on power loss. A real
  product needs flash/EEPROM/FRAM or a small backup supply.
- **Symmetric keys.** `K` is in the chip and in the operator database. A database
  leak leaks all keys, and the station must reach the server. The product path
  is asymmetric signing (ECDSA), at the cost of a much larger RTL footprint.
- **Pack-level voltage only.** One bad cell can be hidden by the pack voltage.
  A richer product records per-cell voltage, current, and temperature.
- **Fixed key in the demo.** All demo chips use `bytes(range(32))`. Production
  derives a unique key per chip from an RO-PUF.
- **No physical tamper resistance.** A lab attacker with decapping equipment is
  outside the hackathon scope.

### 1.6 Why this matters commercially

- A battery pack is a large fraction of an EV's cost (the pitch says ~40%).
- Operators lose money to packs that are abused, stolen, or fraudulently
  warrantied.
- Regulators (e.g. EU Battery Passport) increasingly require lifecycle data
  integrity.

---

## 2. End-to-end flows

### 2.1 Current implemented flow (Flow A — MicroBlaze + firmware)

This is the flow that exists in the repository today and that produced the
Basys 3 artifacts.

```
Station (PC, Python)                         Basys 3 (Flow A fallback)
────────────────────                         ─────────────────────────
AUTH_REQ(nonce 32B)  ───── UART 115200 ────→ AXI UART Lite
                                             MicroBlaze firmware
                                               msg = nonce ‖ ID(4) ‖ V(2)
                                               write key + msg to HMAC IP
                                               HMAC IP: 4 × SHA-256 blocks
AUTH_RESP(ID, V, HMAC 32B) ←──── UART ────── read hash, send frame
verify HMAC
check nonce reuse
check DB lock
```

Properties:

- Voltage is a **fixed 3700 mV** in `fpga/fw/sebatt_fw.c`. There is no ADC in
  this flow.
- The key is a fixed array in firmware (`default_key`), and also written to the
  HMAC IP over AXI.
- The chip's `locked` variable is informational; the station's database lock is
  what actually rejects the battery.
- This flow is **frozen as a fallback** and for recording video. It is not the
  KV260 demo path because the proposal promises no soft processor.

### 2.2 Target flow (Flow B — pure RTL)

This is what the demo must become.

```
                 ┌──────────────────────── FPGA (chip) ─────────────────────────┐
 voltage source  │  ads1115_ctrl ──→ auth_ctrl ──→ hmac_sha256 ──→ uart_if ──→ PC │
 (pot + ADS1115  │                   │  seq counter                            │
  over I2C, or   │                   │  64-record buffer                       │
  switch / ramp) │                   │  lock after 3 failures                  │
                 │                   └── key_vault / ro_puf                     │
                 └─────────────────────────────────────────────────────────────┘
```

Implemented history exchange:

1. Station sends `READ_HIST_REQ` with a fresh 32-byte nonce.
2. Chip returns `N`, the seq range, each record `seq(4) ‖ voltage(2) ‖ tag(32)`,
   and a summary tag over nonce + range.
3. Station recomputes the summary/record tags and checks `seq` is contiguous
   from its anchor.
4. Station updates `last_seq` only after full verification, and sends `RESULT`.

The message layout, sequence semantics, and verification order are described in
Sections 3 and 4 and implemented in `model/protocol.py` and `rtl/auth_ctrl.v`;
the cocotb suite checks a full 64-record dump byte-for-byte.

### 2.3 Attack → detection table

| Attack | What the attacker does | What breaks |
|---|---|---|
| Delete records | Drops seq 150–152 | Station expects 150 next but sees 153 |
| Edit a value | Changes 2.0 V to 3.6 V | HMAC computed over 2.0 V no longer matches |
| Forge a tag | Recomputes HMAC for 3.6 V | No key `K` |
| Replay | Re-sends an old valid response | Nonce is fresh and single-use |
| Roll back | Cuts power, counter restarts | `last_seq` in DB is larger than chip's `seq` |
| Clone identity | Copies a valid pack's ID | Key differs per chip (production), PUF binding |
| Hide abuse by swapping pack | Uses another pack's identity | Identity + history are bound together |

---

## 3. Cryptography

### 3.1 SHA-256

Implementation: [`model/sha256.py`](model/sha256.py) and
[`rtl/sha256_core.v`](rtl/sha256_core.v).

- Standard FIPS 180-4: 64-round compression, 512-bit blocks, big-endian words.
- Message schedule `W[0..63]`; 64 constants `K[0..63]`.
- Padding: append `0x80`, zeros, then the original bit length as a 64-bit
  big-endian integer.
- The Python file has two interfaces:
  - `sha256(message)` — one-shot.
  - `SHA256Core` — stateful `update()` / `digest()`, which mirrors how the RTL
    processes blocks sequentially.
- The RTL core processes one 512-bit block in **113 cycles**:
  - 48 cycles to expand `W[16..63]`,
  - 64 cycles for the compression rounds,
  - 1 cycle to add the working variables back into the hash state.
- It exposes `init_i`, `start_i`, `done_o`, and a 16-word load port. The HMAC
  wrapper loads each block through that port.

Important RTL detail: `w[0..15]` are loaded while `ready_o = 1`; `start_i`
begins expansion. `init_i` resets the hash state to `H_INIT`. The core can be
reused block after block, which is what makes HMAC fit in a small area.

### 3.2 HMAC-SHA-256

Implementation: [`model/hmac.py`](model/hmac.py) and
[`rtl/hmac_sha256.v`](rtl/hmac_sha256.v).

```
HMAC(K, m) = SHA256((K ⊕ opad) ‖ SHA256((K ⊕ ipad) ‖ m))
```

- Block size 64 bytes, output 32 bytes.
- Keys longer than 64 bytes are hashed first; shorter keys are zero-padded.
- `ipad = 0x36` repeated, `opad = 0x5C` repeated.
- The RTL wrapper assumes the key fits in the 8 × 32-bit key registers (32
  bytes). The Python model also handles longer keys, but the current hardware
  path does not. This is fine for the demo (32-byte key), but it is a documented
  limitation.

RTL structure (`hmac_sha256.v`):

- Four SHA-256 block operations:
  1. `K ⊕ ipad` (64 B)
  2. `message + padding` (64 B) → inner hash
  3. `K ⊕ opad` (64 B)
  4. `inner hash + padding` (64 B) → final HMAC
- A small FSM (`H_INIT_INNER`, `H_LOAD_IPAD`, `H_RUN_IPAD`, ... `H_DONE`)
  drives load/start/wait for each block.
- The wrapper only supports a message length ≤ 55 bytes so that the message
  plus SHA padding fits in one 64-byte block. The SeBatt auth message is 38
  bytes, so this is enough today. A future 64-record history dump must not push
  individual records past this limit; each record is signed separately.
- Approximate hardware latency: 4 × 113 ≈ 452 cycles, plus load/FSM overhead.

AXI4-Lite register map (also in `fpga/README.md`):

| Offset | Name | Access | Meaning |
|---|---|---|---|
| `0x00` | CTRL | W | bit0 = start (auto-clear), bit1 = init (auto-clear) |
| `0x04` | STATUS | R | bit0 = done, bit1 = busy |
| `0x08` | MSG_LEN | R/W | message length in bytes (default 38) |
| `0x10–0x2C` | KEY[0..7] | R/W | 256-bit key, big-endian words |
| `0x30–0x6C` | MSG[0..15] | R/W | up to 64-byte message |
| `0x70–0x8C` | HASH[0..7] | R | 256-bit HMAC result |

### 3.3 Message layouts (current)

Authentication (`AUTH_REQ` / `AUTH_RESP`):

```
AUTH_REQ payload  = nonce(32)

signed message    = 0x41 ‖ nonce(32) ‖ battery_id(4) ‖ voltage_mv(2, big-endian)
AUTH_RESP payload = battery_id(4) ‖ voltage_mv(2, big-endian) ‖ HMAC(32)
```

- `battery_id` is 4 bytes, e.g. `BAT\x01` = `42 41 54 01`.
- `voltage_mv` is a 16-bit big-endian integer in millivolts, taken from the
  latest periodic ADS1115 sample (`SAMPLE_INTERVAL_MS`, default 1000 ms), not
  from a conversion started by `AUTH_REQ`.
- Nonce is 32 random bytes from `os.urandom`.
- Tags are compared with `==` in Python. In production, use a constant-time
  comparison to avoid timing side channels. This is not a concern for the
  hackathon demo but is worth knowing.

### 3.4 History record (implemented in Python and RTL)

```
READ_HIST_REQ  = 0x07   payload: nonce(32)
READ_HIST_RESP = 0x08   payload: N(1) ‖ seq_oldest(4) ‖ seq_last(4)
                                  ‖ N × record(38) ‖ summary_tag(32)
record         = seq(4, big-endian) ‖ voltage(2, big-endian) ‖ tag(32)

record_tag_i = HMAC(K, 0x53 ‖ ID ‖ seq_i ‖ V_i)
summary_tag  = HMAC(K, 0x48 ‖ nonce ‖ ID ‖ seq_oldest ‖ seq_last)
```

- The chip signs each record when it is stored, so a dump costs one summary
  HMAC plus the UART transfer.
- Each record is 38 bytes. A full dump payload is 2473 bytes (about 215 ms at
  115200 baud), which is acceptable for a 0.5 s dashboard poll.
- The station's per-battery anchor is `{last_seq, last_seen_time}`.
- A gap at the **start** of the buffer means old records were overwritten
  (ring-buffer truncation, not fraud). A gap in the **middle** means records
  were dropped in transit (fraud).
- Optionally, chain the tags: `tag_i = HMAC(K, ID ‖ seq_i ‖ V_i ‖ tag_{i-1})`.
  This makes deletion detectable even without a station anchor, but it is more
  complex and is iteration 2.

### 3.5 Keys and key management

**Current demo**

- Fixed key: `bytes(range(32))` = `00 01 02 ... 1F`.
- In Python: `KeyVault` default in [`model/ro_puf.py`](model/ro_puf.py).
- In RTL: hard-coded default in [`rtl/key_vault.v`](rtl/key_vault.v).
- In Flow A firmware: `default_key[8]` in
  [`fpga/fw/sebatt_fw.c`](fpga/fw/sebatt_fw.c).
- In the station: `IdentityDB.register(b'BAT\x01', bytes(range(32)))` in
  [`model/station.py`](model/station.py).

**Target product**

- Each chip gets a unique key derived from an RO-PUF.
- The key is never stored in plaintext NVM; it is reconstructed on demand.
- The station holds only public keys if the scheme moves to ECDSA.
- In the short term, the operator database holds the symmetric key, so the
  station must be online or have a secure local cache.

### 3.6 Domain separation (target)

The technical narrative specifies a one-byte prefix in the signed message:

- `0x53` for a history record (`ID ‖ seq ‖ V`),
- `0x41` for a nonce response (`nonce ‖ ID ‖ last_seq ‖ V`).

This prevents a signature produced for one purpose from being reused for the
other. The history prefix also has a 0x48 summary variant. Python and RTL use
all three prefixes as of 21 Oct, and the test vectors were regenerated; the
Flow A firmware still needs the 0x41 prefix so its vectors match.

---

## 4. Wire protocol (UART)

Implementation: `WireProtocol` in [`model/protocol.py`](model/protocol.py),
and duplicated in C in [`fpga/fw/sebatt_fw.c`](fpga/fw/sebatt_fw.c).

### 4.1 Frame format

```
[CMD:1][LEN:2, big-endian][PAYLOAD:LEN][CRC8:1]
```

- `CMD` is one byte.
- `LEN` is the payload length in bytes, big-endian.
- `CRC8` is computed over `CMD + LEN + PAYLOAD`.
- The polynomial is `0x31`, MSB-first, init `0x00` (CRC-8/MAXIM-style). The same
  implementation exists in Python, C, and is small in RTL.
- The receiver must reject a frame if the CRC does not match.

### 4.2 Commands

| Value | Name | Direction | Payload |
|---|---|---|---|
| `0x01` | `AUTH_REQ` | station → chip | nonce(32) |
| `0x02` | `AUTH_RESP` | chip → station | ID(4) + V(2) + HMAC(32) |
| `0x03` | `RESULT` | station → chip | status(1) |
| `0x04` | `LOCK` | station → chip | none |
| `0x05` | `UNLOCK` | station → chip | none |
| `0x06` | `STATUS` | station → chip | none |
| `0x07` | `READ_HIST_REQ` | station → chip | nonce(32) |
| `0x08` | `READ_HIST_RESP` | chip → station | count(1) + range + records + summary tag |

### 4.3 Status codes

| Value | Name | Meaning |
|---|---|---|
| `0x00` | `VALID` | signature and nonce are valid |
| `0x01` | `INVALID_HMAC` | signature does not match |
| `0x02` | `REPLAY_DETECTED` | nonce was already used |
| `0x03` | `BATTERY_LOCKED` | battery is blocked in the database |
| `0x04` | `UNKNOWN_BATTERY` | ID is not registered |

### 4.4 Verification order in the station

The current Python order is:

1. Look up the battery ID. Unknown → `UNKNOWN_BATTERY`.
2. Check the DB lock flag. Locked → `BATTERY_LOCKED`.
3. Check whether the nonce was used before. Reused → `REPLAY_DETECTED`.
4. Mark the nonce as used.
5. Recompute `HMAC(K, nonce ‖ ID ‖ V)` and compare. Mismatch →
   `INVALID_HMAC`.
6. Otherwise `VALID` and increment the auth counter.

Note: the nonce is added to the used set **before** the HMAC check. That means a
failed HMAC still consumes the nonce. This is acceptable for the demo, but a
production design should think about whether that helps or hurts retry behavior.

### 4.5 History verification order (target)

1. Verify the response tag over the nonce.
2. Verify each record tag.
3. Verify `seq` is contiguous from `last_seq + 1` (or from the oldest buffered
   record if the buffer wrapped).
4. Only then update `last_seq` and render the health card.
5. A rejected history shows "Riwayat: TIDAK DAPAT DIPERCAYA" and no numbers.

---

## 5. Repository map

```
sebatt/
├── README.md                 Project summary and team
├── context.md                This document
├── docs/
│   ├── catatan-teknis/       Technical narrative, demo, board plan, meeting notes
│   ├── gambar/               Diagrams (alur-teknis, alur-demo)
│   ├── ketentuan.md          Competition rules summary
│   ├── MILESTONES.md         Schedule and task ownership
│   ├── proposal/             LaTeX mini proposal
│   └── kirim/                Submitted PDFs
├── model/                    Python golden reference + station emulator
│   ├── sha256.py             Pure-Python SHA-256
│   ├── hmac.py               HMAC-SHA-256
│   ├── ro_puf.py             Behavioral RO-PUF + KeyVault
│   ├── protocol.py           Protocol model + wire framing
│   ├── station.py            Hardware station emulator / CLI / demo
│   ├── gen_vectors.py        Test vector generator (JSON + .mem)
│   ├── test_model.py         40 unit tests
│   └── vectors/              Generated vectors
├── rtl/
│   ├── sha256_core.v         SHA-256 compression engine
│   ├── hmac_sha256.v         HMAC wrapper + AXI4-Lite slave
│   ├── key_vault.v           Fixed key store (stage 1)
│   ├── ro_puf.v              RO-PUF (stage 2, behavioral/synthesis)
│   ├── i2c_master.v          I2C master (100 kHz) for the ADS1115
│   ├── ads1115_ctrl.v        ADS1115 config/read FSM, outputs mV
│   ├── uart_if.v             UART 8N1 byte interface
│   ├── axil_master.v         AXI4-Lite master for the HMAC registers
│   ├── auth_ctrl.v           Frame parser + auth FSM + HMAC glue
│   └── sebatt_top.v          Flow B top level
├── sim/
│   ├── Makefile              cocotb targets (sha256, hmac, ads1115, auth)
│   ├── test_sha256.py        5 tests
│   ├── test_hmac.py          4 tests
│   ├── test_ads1115.py       ADS1115 I2C model + controller tests
│   ├── tb_auth.v             12 MHz wrapper for the auth tests
│   └── test_auth_ctrl.py     12 auth/history tests (UART, lock, READ_HIST, dump race, parser resync)
├── fpga/
│   ├── README.md             Flow A build/run guide
│   ├── create_bd.tcl         MicroBlaze + AXI UART Lite + HMAC BD
│   ├── package_ip.tcl        Package HMAC as AXI IP
│   ├── fw/sebatt_fw.c        MicroBlaze firmware
│   ├── ws/                   Vitis workspace + built .elf/.bit artifacts
│   ├── basys_3/              Basys 3 Vivado project
│   ├── nexys_a7/             Nexys A7 Vivado project
│   ├── cmod_s7/              Flow B Cmod S7 build + bitstream
│   └── kv260/                KV260 PS clock BD + Pmod bitstream + RUNBOOK
├── bisnis/                   Business model and lean canvas
├── pitch/                    Pitch deck and comparison notes
└── tools/preflight_basys3.sh Preflight script (optional)
```

Important: the repo contains **Flow A** artifacts, the **core crypto RTL**,
and the Flow B chain (`ads1115_ctrl`/`i2c_master`, `uart_if`, `axil_master`,
`auth_ctrl`, `sebatt_top`). The history protocol (READ_HIST, seq counter,
64-record signed log, lock) is implemented in `auth_ctrl` and the Python
model.

---

## 6. Code walkthrough

### 6.1 Python model (`model/`)

The Python model is the executable specification. Every RTL change should be
checked against it.

#### `model/sha256.py`

- `K[64]` and `H_INIT[8]` constants.
- Helper functions `_rotr`, `_shr`, `_ch`, `_maj`, `_sigma0`, `_sigma1`,
  `_gamma0`, `_gamma1`.
- `_pad(message)` implements FIPS padding.
- `sha256(message)` returns 32 bytes.
- `SHA256Core` is stateful:
  - `update(data)` consumes complete 64-byte blocks and buffers the remainder.
  - `digest()` applies padding to a copy and returns the hash without mutating
    the object.
- This class exists specifically so the Python and RTL block flow match.

#### `model/hmac.py`

- `hmac_sha256(key, message)` implements RFC 2104 / RFC 4231.
- It hashes keys longer than 64 bytes, zero-pads short keys, XORs with
  `0x36` / `0x5C`, and calls `sha256` twice.
- `hmac_sha256_hex` is a convenience wrapper.
- This is the reference used by the station and by the test-vector generator.

#### `model/ro_puf.py`

- `ROPUFConfig`: number of ROs, count window, noise, key bits, repetition code.
- `PUFInstance`: per-chip base oscillator counts, helper data, enrolled flag.
- `ROPUFModel`:
  - `create_instance()` simulates manufacturing variation.
  - `read_raw()` adds Gaussian noise.
  - `generate_response()` compares adjacent RO pairs.
  - `enroll()` does a majority vote over repeated reads and derives a 32-byte
    key via SHA-256.
  - `reconstruct_key()` uses helper data to reproduce the key.
  - `hamming_distance()` is a utility for inter/intra-chip statistics.
- **Honest limitation:** the "fuzzy extractor" here is a behavioral
  simplification. `reconstruct_key()` effectively returns the stable bits from
  helper data, so it trivially matches enrollment. Real hardware needs error
  correction (repetition/BCH) and a helper-data scheme that does not leak the
  key.
- `KeyVault` is the stage-1 fixed key store, defaulting to `bytes(range(32))`.

What you need to be able to say: RO-PUF turns manufacturing variation into a
chip-unique fingerprint; the key is reconstructed, not stored; stage 1 uses a
fixed key so the rest of the system can be built and tested first.

#### `model/protocol.py`

- `AuthStatus` and `Command` enums.
- Dataclasses: `Battery`, `AuthRequest`, `AuthResponse`.
- `SeBattChip`:
  - constructor takes `battery_id`, `key`, `voltage_mv` (default 3700),
  - `set_voltage()` simulates a new ADC reading,
  - `handle_auth_request()` builds `nonce ‖ ID ‖ V`, computes HMAC, returns a
    response.
- `Station` (model):
  - `register_battery()`, `lock_battery()`, `unlock_battery()`,
  - `generate_challenge()` uses `os.urandom(32)`,
  - `verify_response()` implements the five-step order in Section 4.4,
  - `authenticate(chip)` is a convenience full flow.
- `WireProtocol`:
  - `encode_auth_req`, `encode_auth_resp`, `encode_result`,
  - `decode`, `decode_auth_req`, `decode_auth_resp`, `decode_result`,
  - `_frame` and `_crc8`.
- This file is the contract. The firmware and RTL must reproduce it byte for
  byte.

#### `model/station.py`

This is the **hardware** station, not the pure model. It talks to the board over
serial.

- `IdentityDB`: in-memory battery records and used nonces.
- `Station`:
  - opens `serial.Serial(port, baudrate=115200, timeout=2.0)`,
  - registers `BAT\x01` with `bytes(range(32))` by default,
  - `_send_frame` / `_recv_frame` implement the same frame format and CRC,
  - `authenticate()` sends `AUTH_REQ`, receives `AUTH_RESP`, verifies the HMAC,
    replay, and lock status,
  - `lock_battery()` / `unlock_battery()` send `LOCK` / `UNLOCK` and update the
    local DB.
- `run_demo(station)`: valid auth, repeated auth, lock, unlock.
- `run_benchmark(station, count)`: throughput/latency.
- `run_offline_test(demo_mode)`: no hardware; uses `model.protocol` classes.
  This is what passed in the preflight.
- `find_uart_port()`: scans USB serial ports; ignore `/dev/ttyS*`.
- CLI:
  - `--port`, `--baud`, `--demo`, `--benchmark`, `--count`, `--offline`,
    `--interactive`.
- If no port is found and `--demo` is used, it falls back to the offline demo.

Difference to keep clear:

- `model.protocol.Station` is an in-memory verifier used for unit tests and the
  offline demo.
- `model.station.Station` is the UART client used against the FPGA.

#### `model/gen_vectors.py`

- `fips_sha256_vectors()`: FIPS B.1 and B.2, verified against the Python
  implementation.
- `rfc4231_hmac_vectors()`: RFC 4231 cases 1, 2, 3, 4, 6, 7.
- `sebatt_protocol_vectors(count=20)`: deterministic nonces, IDs, voltages,
  and MACs.
- `generate_all()` writes:
  - `sha256_vectors.json`,
  - `hmac_vectors.json`,
  - `protocol_vectors.json`,
  - `.mem` files for Verilog `$readmemh` under `model/vectors/mem/`.
- The cocotb tests currently hard-code their expected values, but the vector
  files are the bridge if you want data-driven tests.

#### `model/test_model.py`

40 tests, all passing:

- SHA-256: FIPS B.1/B.2, empty string, single byte, 55/56-byte boundaries,
  stateful vs one-shot, incremental update.
- HMAC: RFC 4231 cases 1–4 and 6, long key, empty message.
- RO-PUF: key vault behavior, instance creation, enrollment/reconstruction,
  different instances produce different keys, inter/intra Hamming distance.
- Protocol: valid auth, multiple auths, unknown battery, lock/unlock, replay,
  wrong key, voltage tampering, auth count, log.
- Wire protocol: request/response/result round trips, CRC corruption, short
  frame.

Run:

```bash
source .venv/bin/activate
python3 -m pytest model/test_model.py -q
# 40 passed
```

### 6.2 RTL (`rtl/`)

#### `rtl/sha256_core.v`

- FSM: `S_IDLE → S_EXPAND → S_ROUND → S_DONE`.
- `w[0..63]` message schedule; `h0..h7` hash state; `va..vh` working variables.
- `ready_o` is high in `S_IDLE`; `done_o` pulses in `S_DONE`.
- `hash_o` is the current 256-bit digest.
- K constants are a `case` function; arithmetic is 32-bit modular.
- Cycle count: 48 + 64 + 1 ≈ 113 per block. The cocotb test asserts ≤ 120.
- This is the area-efficient design: one round per cycle, one shared core.

What to master: why the message schedule is expanded first, why `init_i` must
be asserted between messages, and why `ready_o` gates loading.

#### `rtl/hmac_sha256.v`

- Instantiates one `sha256_core` and reuses it four times.
- AXI4-Lite slave with separate write/read FSMs.
- Key and message registers are plain registers, not a key vault.
- The HMAC FSM:
  - `H_INIT_INNER → H_LOAD_IPAD → H_RUN_IPAD`
  - `H_LOAD_MSG → H_RUN_MSG` (saves inner hash)
  - `H_INIT_OUTER → H_LOAD_OPAD → H_RUN_OPAD`
  - `H_LOAD_FINAL → H_RUN_FINAL → H_DONE`
- Message padding is generated on the fly while loading the second block.
- `MSG_LEN` must be ≤ 55 for the current single-block message path.
- `STATUS` bit0 = done, bit1 = busy.
- `CTRL` bits are auto-cleared pulses.

Known sharp edges:

- The read map for `0x00` packs `{hmac_done, hmac_busy, 2'b00}`; `0x04` is the
  documented status register. Use `0x04`.
- AXI write and read FSMs are simple and assume a well-behaved master. They are
  adequate for MicroBlaze and cocotb, not a general-purpose AXI verification.
- The key path is writable over AXI. In the target product, the key must come
  from `key_vault`/PUF and must not be readable or writable from software.

#### `rtl/key_vault.v`

- 8 × 32-bit registers, default `0x00010203 ... 0x1C1D1E1F`.
- `key_o` concatenates the words for direct connection to the HMAC core.
- `wr_en_i` allows test/PUF enrollment writes. In production, remove the write
  port or make it one-time programmable.
- Not instantiated by `hmac_sha256.v` yet. Flow A writes the key over AXI
  instead.

#### `rtl/ro_puf.v`

- `NUM_PAIRS` pairs of ring oscillators, `COUNT_WINDOW` cycles.
- Each `ro_cell` is a 3-inverter loop enabled by `ro_en`.
- Counters count RO edges; after the window, `ro_cnt_a > ro_cnt_b` gives one bit.
- `SYNTHESIS` branch uses `DONT_TOUCH`/`KEEP` to stop Vivado from optimizing the
  oscillators away.
- Behavioral branch models process variation with a per-instance `SEED`.

Known sharp edges:

- Asynchronous counters driven by combinational ring oscillators are not
  portable FPGA design practice. This block is stage 2 and is not integrated
  into Flow A or the current demo.
- The RTL has no fuzzy extractor/helper-data logic; the Python model has a
  simplified one. Do not claim the PUF is production-ready.

### 6.3 Simulation (`sim/`)

- `Makefile` targets:
  - `make sha256` → `TOPLEVEL=sha256_core`, `MODULE=test_sha256`;
  - `make hmac` → `TOPLEVEL=hmac_sha256`, `MODULE=test_hmac`;
  - `make ads1115` → `TOPLEVEL=ads1115_ctrl`, `MODULE=test_ads1115`;
  - `make auth` → `TOPLEVEL=tb_auth`, `MODULE=test_auth_ctrl`;
  - `make all`, `make clean`.
- Uses Icarus Verilog (`SIM=icarus`) and cocotb 2.1.0 from `.venv`.
- `test_sha256.py`:
  - FIPS "abc",
  - two-block FIPS B.2,
  - empty string,
  - `init_i` resets state between messages,
  - cycle count ≤ 120.
- `test_hmac.py`:
  - RFC 4231 cases 1, 2, 3,
  - SeBatt protocol vector (`nonce=bytes(range(32))`, `BAT\x00`, 3000 mV).
- `test_ads1115.py`: behavioral ADS1115 model; 2 tests (3300 mV and 2000 mV /
  0 mV raw values).
- `test_auth_ctrl.py`: 9 tests against `model.hmac`/`model.protocol` — normal
  AUTH_RESP, second nonce, bad CRC ignored, unknown command ignored, lock
  state, LOCK/UNLOCK/CHIP_LOCKED, lock after three failed RESULTs, the periodic
  `adc_start` interval (12 000 cycles in the TB, 1 s in hardware), and a
  full 64-record READ_HIST dump checked byte-for-byte.
- Drivers model AXI4-Lite transactions manually (`axi_write`, `axi_read`,
  `start_and_wait`, `read_hash`).

**Important operational note:** Icarus reuses `sim_build/sim.vvp` across
targets. `make all` now runs `make clean` between each target. A standalone
target after another target still needs `make clean` first, otherwise you can
get `RuntimeError: Can not find root handle` or a stale DUT. Verified:

```bash
source .venv/bin/activate
cd sim
make clean
make sha256   # TESTS=5 PASS=5
make clean
make hmac     # TESTS=4 PASS=4
make clean
make ads1115  # TESTS=2 PASS=2
make clean
make auth     # TESTS=9 PASS=9
```

Total: 23/23.

### 6.4 FPGA Flow A (`fpga/`)

#### `fpga/fw/sebatt_fw.c`

- UART: Xilinx `XUartLite` driver.
- Frame receive: reads `CMD`, `LEN` (big-endian), payload, CRC; returns negative
  on length error or CRC error.
- Frame send: builds header + payload + CRC.
- HMAC driver:
  - writes 8 key words from `default_key`,
  - writes `MSG_LEN` and message words (big-endian packing),
  - writes `CTRL=START`, polls `STATUS` for done,
  - reads 8 hash words and converts to bytes.
- `handle_auth_req()`:
  - builds `nonce ‖ battery_id ‖ voltage_mv`,
  - loads key/message, starts HMAC, reads result,
  - sends `AUTH_RESP` with `ID ‖ V ‖ HMAC`.
- `main()`: initializes UART, prints banner, loops over frames, handles
  `AUTH_REQ`, `LOCK`, `UNLOCK`, `STATUS`.
- `voltage_mv` is fixed at 3700 in Flow A. The Flow B voltage source is the
  ADS1115 over I2C (`ads1115_ctrl` + `i2c_master`).
- `locked` is local and does not gate `handle_auth_req()`; the station's DB is
  what rejects locked batteries.

#### `fpga/create_bd.tcl`

- Creates a Vivado project for `xc7a100tcsg324-1` (Nexys A7-100T).
- Adds `sha256_core.v`, `hmac_sha256.v`, `key_vault.v`.
- Creates a MicroBlaze subsystem with 128 KB local memory and debug.
- Adds an AXI UART Lite at 115200.
- Adds the HMAC module as an AXI slave at `0x44A00000`.
- Exposes `sys_clk`, `sys_resetn`, `uart_rxd`, `uart_txd`.
- Adds `nexys_a7.xdc`.
- Prints the address map and next synthesis commands.

Address map:

| Peripheral | Base | Size |
|---|---|---|
| BRAM | `0x00000000` | 128 KB |
| AXI UART Lite | `0x40600000` | 64 KB |
| HMAC-SHA-256 | `0x44A00000` | 4 KB |

#### `fpga/package_ip.tcl`

- Creates a temporary project, adds the SHA/HMAC RTL, sets `hmac_sha256` as top.
- Packages it as `sebatt:ip:hmac_sha256:1.0`, infers the AXI4-Lite interface,
  sets a 256-byte register range, associates `S_AXI` with `s_axi_aclk`.
- Output goes to `fpga/ip_repo/hmac_sha256_1.0/`.

#### Board constraints

- `fpga/nexys_a7/nexys_a7.xdc` is the real Nexys A7 constraint (clock E3,
  reset C12, UART C4/D4).
- `fpga/basys_3/nexys_a7.xdc` is misnamed: its contents are still Nexys A7 pins
  (E3/C12/C4/D4). The Basys 3 Vivado project references a generated
  `constrs_1/new/basys_3.xdc`. Before any Basys 3 bitstream build, create a
  proper Basys 3 XDC using the pin table in Section 9. Do not reuse the Nexys
  file.
- The Basys 3 artifacts in `fpga/ws/` (`.bit`, `.elf`, `.xsa`) exist and are
  non-zero, but they were produced before this document and were not re-tested
  here.

### 6.5 `tools/`

- `tools/preflight_basys3.sh`: optional script version of the Fase 0 checks.
  The test plan recommends doing the checks manually first.

---

## 7. How the pieces connect

### 7.1 One source of truth

The compatibility chain is:

```
model/sha256.py + model/hmac.py      (golden crypto)
            │
            ├── model/gen_vectors.py → vectors JSON/.mem
            │
            ├── model/protocol.py    (golden frames and status)
            │        │
            │        ├── model/station.py → talks to hardware
            │        │
            │        └── fpga/fw/sebatt_fw.c → must match byte-for-byte
            │
            └── rtl/sha256_core.v + rtl/hmac_sha256.v → must match vectors
```

Rules:

1. If the Python model and RTL disagree, **fix the RTL**, not the model, unless
   the model is provably wrong.
2. Any protocol byte change must be made in `model/protocol.py`,
   `model/station.py`, `fpga/fw/sebatt_fw.c`, and the RTL at the same time.
3. Regenerate vectors after any crypto change.
4. Never let software touch the voltage value before it is signed. Software may
   only modify data **after** signing — that is the attacker's role.

### 7.2 The data-path rule

> Software may change data **after** it is signed — that is the BMS attack.
> Software must never touch it **before** it is signed.

Consequences:

- The demo voltage source must be a pin/RTL source: switches, XADC, a scripted
  ramp, or the ADS1115 (I2C) connected to the FPGA.
- Do not feed the voltage from the PS (Zynq ARM), PYNQ, AXI, or UART. If you do,
  the sample passes through software before signing, and the central claim
  collapses.
- The station verifies only values that arrive inside a signed frame. It must
  not trust a separate "current voltage" field.

### 7.3 Flow A vs Flow B

| | Flow A | Flow B |
|---|---|---|
| Compute | MicroBlaze + C firmware | pure RTL |
| Voltage | fixed 3700 mV | ADS1115 (I2C) / switch / scripted ramp |
| History | none | 64-record signed ring buffer |
| Status | fallback; Basys 3 reset bug open | auth chain + periodic sampling + signed history + lock built; Cmod S7 bitstream rebuilt; board run pending |
| KV260 | not portable (soft CPU) | portable |
| Purpose | fallback, video, hardware smoke test | real demo |

Flow A is frozen. Do not invest more in it except to record the fallback video
and validate the board.

---

## 8. Running everything

### 8.1 Python unit tests

```bash
source .venv/bin/activate
python3 -m pytest model/test_model.py -q
# 40 passed
```

### 8.2 Offline station demo

```bash
source .venv/bin/activate
python3 -m model.station --offline --demo
```

Expected end:

```
Demo completed successfully. All security scenarios verified.
```

The offline demo covers:

1. legitimate authentication → `VALID`,
2. replay → `REPLAY_DETECTED`,
3. voltage tampering → `INVALID_HMAC`,
4. locked battery → `BATTERY_LOCKED`,
5. 1000-auth benchmark (about 330 auth/s on this laptop).

### 8.3 Generate vectors

```bash
source .venv/bin/activate
python3 -m model.gen_vectors
```

Writes JSON and `.mem` files under `model/vectors/`.

### 8.4 RTL simulation

```bash
source .venv/bin/activate
cd sim
make clean
make sha256   # 5/5
make clean
make hmac     # 4/4
```

If you see `Can not find root handle`, you skipped `make clean` between targets.

### 8.5 Station against a board

```bash
# board connected, UART is usually /dev/ttyUSB1 on Basys/Nexys FT2232
source .venv/bin/activate
python3 -m model.station --port /dev/ttyUSB1 --demo
python3 -m model.station --port /dev/ttyUSB1 --interactive
python3 -m model.station --port /dev/ttyUSB1 --benchmark --count 1000
```

### 8.6 Flow A build (summary)

```bash
# Package IP
cd fpga
vivado -mode batch -source package_ip.tcl

# Create block design
cd nexys_a7
vivado -mode batch -source ../../fpga/create_bd.tcl

# In Vivado
launch_runs synth_1 -jobs 4
wait_on_run synth_1
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
write_hw_platform -fixed -include_bit -file sebatt_bd_wrapper.xsa
```

Then build the firmware in Vitis from the `.xsa`, program the bitstream, and run
the station. The full board sequence with test IDs T1–T9 is in
`docs/catatan-teknis/rencana-tes-basys3.md`.

---

## 9. Board bring-up (Cmod S7 practice, KV260 demo day)

> 19 Oct change: the team has no Basys 3 / Nexys A7 for demo day. Practice and
> fallback recording use the **Cmod S7**; the hackathon stage uses the **KV260**.
> The Basys 3 section below is kept because the frozen Flow A artifacts target
> it; the RTL Flow B chain targets `xc7s25csga225-1` (Cmod S7, confirmed in
> Vivado) and `xck26` (KV260).

### 9.1 Basys 3 pin table (from the test plan)

| Signal | Pin |
|---|---|
| Clock 100 MHz | `W5` |
| Reset | `U18` (btnC) |
| UART RX (from FTDI) | `B18` |
| UART TX (to FTDI) | `A18` |
| `SW[0]` | `V17` |
| `SW[1]` | `V16` |
| `SW[2]` | `W16` |
| `SW[3]` | `W17` |
| `SW[4]` | `W15` |
| `SW[5]` | `V15` |
| `SW[6]` | `W14` |
| `SW[7]` | `W13` |
| `LED[0]` | `U16` |
| `LED[1]` | `E19` |
| `LED[2]` | `U19` |
| `LED[3]` | `V19` |

Frozen voltage mapping for the RTL test:

```
V_mV = 3000 + sw[7:0] * 5      → 3000–4275 mV
```

The station trusts only the value inside the signed frame.

### 9.2 Board test sequence (T1–T9)

1. **Preflight**: FTDI visible, `/dev/ttyUSB1`, `dialout`, artifacts exist,
   hw_server 2024.1, `.venv`, offline demo.
2. **T1**: program `sebatt_bd_wrapperbasys3.bit` through Hardware Manager at
   `localhost:3121`.
3. **T2**: run `app_component` from Vitis. One timeout message is allowed; the
   hart should halt. Fallback: `connect; targets; rst -processor; dow <elf>; con`.
4. **T3**: `python3 -m model.station --port /dev/ttyUSB1 --demo` → VALID,
   REPLAY_DETECTED, INVALID_HMAC, BATTERY_LOCKED.
5. **T4**: record 60–90 s fallback video. Back it up in two places. This is
   mandatory.
6. **T5**: ~~build the RTL bitstream.~~ Rebuilt 21 Oct for the Cmod S7
   (`xc7s25csga225-1`, top `cmod_s7_top`); WNS +55.788 ns.
7. **T6**: program `fpga/cmod_s7/build/cmod_s7_top.bit`; heartbeat LED blinks.
8. **T7**: station `--interactive` → `auth` → VALID; turn the ADS1115 pot
   (or flip switches) → `auth` → VALID with the new voltage. **T7 PASS is the
   main goal.**
9. **T8** (optional): LED valid/reject.
10. **T9**: scan I2C `0x48`, read AIN0 while turning the pot; `V_mV` follows
    the pot and there is no NACK.

Hard stops from the test plan:

- If T7 is not VALID by 15:00, stop RTL work.
- Record the fallback video before going home.

### 9.3 KV260 notes

- Built 21 Oct: `kv260_top.v` + `kv260.xdc` + `build.tcl` (PS clock-only block
  design, `pl_clk0` 100 MHz from IOPLL) + `RUNBOOK.md`. Bitstream
  `build/kv260_top.bit`, boot image `build/kv260_top.bit.bin`. Rebuilt after
  the `sg_req*`, dump-race, CRC, and parser-resync fixes; WNS +1.466 ns.
- Logic clock comes from the PS (`pl_clk0`), so the Zynq UltraScale+ block stays
  in the block design as a clock source. There is no PL oscillator on the KV260.
- **Verify `pl0_ref` at ~99.999 MHz and enabled before trusting UART.** Stock
  firmware may use RPLL (96.97 MHz) or gate the clock; see RUNBOOK §5.
- The onboard UART belongs to the PS. The SeBatt UART leaves through Pmod J2
  7/8 + **CP2102/CH340/FT232** (3.3 V logic).
- All 8 Pmod data pins are used: I2C (1/2), `src_sel` (3), heartbeat LED (4), UART
  (7/8), green/red LEDs (9/10). Package pins: H12/E10/D10/C11/B10/E12/D11/B11.
- Load with `fpgautil -b kv260_top.bit.bin` (or JTAG `program.tcl`); unload the
  stock `k26-starter-kits` app first.
- Verify in order: clock check -> load/`dmesg` -> auth valid (green LED) ->
  history -> modified history rejected.

---

## 10. Demo script

The demo is about 60 seconds inside a 5-minute pitch.

### 10.1 Table layout

```
[PAKET BATERAI]        [KV260 "CHIP SeBatt"]      [Laptop BMS curang]      [Laptop stasiun] → projector
 knob + ADS1115 + LED  ──I2C──→  SeBatt logic  ──UART──→  Hapus / Ubah  ──UART──→  dashboard
```

The attacker laptop sits physically in the middle, labelled, so the audience
sees that the attacker is between the battery and the station.

### 10.2 Scenes

**Scene 1 — normal use (~15 s)**

- Guntur: "This is an EV battery pack. The SeBatt chip records its voltage every
  few hours." Turns the knob up and down in the normal zone.
- Screen: graph moves, each point numbered and marked ✓.
- Budi presses "Tukar baterai".
- Screen: green **DITERIMA**; health card shows cycles, deep discharges 0,
  history **TERVERIFIKASI**.

**Scene 2 — deep discharge + deleted records (~25 s)**

- Guntur invites a judge to turn the knob down into the red zone (e.g. 2.0 V).
- Screen: graph drops into red; the event is visibly recorded.
- Guntur: "The battery is now damaged. The owner wants to sell or swap it
  without anyone knowing, so the modified BMS deletes that record."
- Budi presses "Hapus catatan" on the attacker laptop, then "Tukar baterai".
- Brief comparison slide: ordinary BMS would say **DITERIMA**.
- SeBatt dashboard: red **DITOLAK, catatan jam 14–17 hilang**; missing rows
  highlighted.

**Scene 3 — edited value (~15 s)**

- Guntur: "What if instead of deleting it, they change the number?"
- Budi presses "Ubah angka": 2.0 V → 3.6 V, then "Tukar baterai".
- Screen: red **DITOLAK, data diubah**; the edited row is highlighted.
- Guntur: "The BMS can change the number, but it cannot create the signature,
  because the key exists only inside the chip."

**Closing (~5 s)**

- Guntur: "This demo uses low voltage and an external ADC. In the final chip,
  the ADC is inside the same die."

### 10.3 Failure playbook

| Failure | Action |
|---|---|
| Board does not respond in 10 s | Budi plays the fallback video immediately; Guntur narrates along |
| ADC not reading | Dashboard switches to dataset mode; say "input from recorded data" |
| Attacker laptop fails | Skip scenes 2–3 live, play those video segments |
| Projector fails | Turn the station laptop toward the judges |

### 10.4 Q&A answers to rehearse

| Question | Answer |
|---|---|
| "What if the response is replayed?" | Nonce is fresh and single-use → `REPLAY_DETECTED` |
| "What if they keep trying?" | Three consecutive failures → chip locks; red LED |
| "What if power is cut?" | Counter returns to 0; station sees `last_seq` regression and rejects. Admit that production needs NVM |
| "Can the key be read?" | In production, key_vault is write-once/no-read and each chip has its own key |
| "Can the ADC data be spoofed?" | Yes, before it enters the chip. In the final chip the ADC is on the same die |
| "What if the database leaks?" | The symmetric keys leak too; that is the limitation of symmetric crypto. The product path is asymmetric |
| "How is this different from BQ40Z50?" | BQ40Z50 signs/authenticates the **pack identity** with SHA-1; its lifetime log is unsigned, unsequenced, and writable through data flash. SeBatt signs **each sample**, with a sequence number, at the measurement point |
| "How is this different from MAX17205?" | MAX17205 has SHA-256 but still only anti-cloning, not history integrity |
| "Is the PUF real?" | Stage 2. The demo uses a fixed key; the RTL and model for the RO-PUF exist, but the PUF is not in the demo path |

---

## 11. Status, gaps, and known discrepancies

### 11.1 What is done

| Area | Status |
|---|---|
| SHA-256 Python | Complete, FIPS vectors |
| HMAC Python | Complete, RFC 4231 vectors |
| SHA-256 RTL | Complete, 5/5 cocotb tests |
| HMAC RTL + AXI | Complete, 4/4 cocotb tests |
| Key vault RTL | Fixed-key stage 1 |
| RO-PUF model + RTL | Behavioral/stage 2, not integrated |
| Protocol model + wire framing | Auth, history, lock, prefixes |
| Station emulator | Auth, replay, lock, benchmark, offline demo |
| Flow A FPGA | Artifacts built; 19 Oct session found Basys 3 reset-polarity / debug-reset blockers |
| ADS1115 I2C RTL | Done 20 Oct: `i2c_master.v` + `ads1115_ctrl.v` + cocotb model, 2/2 tests pass |
| Flow B auth RTL | Done 20–21 Oct: `uart_if.v`, `axil_master.v`, `auth_ctrl.v`, `sebatt_top.v`; periodic sampling (1 s default), signed 64-record history, READ_HIST, RESULT/LOCK/UNLOCK/STATUS, lock; cocotb `make auth` 12/12 pass |
| Cmod S7 bitstream | Rebuilt 21 Oct: `xc7s25csga225-1`, WNS +55.788 ns, 5 235 LUT / 6 024 FF, 0 BRAM/DSP; hardware run pending |
| KV260 port | Done 21 Oct: PS `pl_clk0` 100 MHz block design, Pmod XDC, full bitstream + `.bit.bin`, RUNBOOK, demo bundle; `sg_req*`/dump-race/CRC/parser fixes; WNS +1.466 ns, 5 633 LUT / 6 201 FF, 0 BRAM/DSP; physical T6/T7/T9/T10 pending |
| Test plan | Written; preflight passes, Flow A blocked by reset bug |
| Periodic ADS1115 sampling | Done: 1 s default demo (`SAMPLE_INTERVAL_MS`), every sample stored and tagged; AUTH_REQ signs the latest sample |
| Flow B history | Done 21 Oct: seq counter, ring buffer, per-record 0x53 tags, 0x48 summary tag; verified against Python in the 12/12 auth suite |
| Business/pitch | Drafts exist |

### 11.2 What is missing (Flow B)

| Missing piece | Why it matters |
|---|---|
| Firmware Flow A prefix sync | Flow A `HMAC(nonce‖ID‖V)` must add 0x41 to match Python/RTL vectors |
| key_vault integration | `auth_ctrl` still writes the key through `axil_master` |
| BMS attacker proxy | Demo scenes 2–3 |
| Cmod S7 hardware run | Program the built bitstream, run T7/T9 on the board |
| KV260 hardware run | Program the bitstream, verify `pl0_ref`, run T6/T7/T9/T10 on the board |
| Fallback video | Insurance for demo day |

### 11.3 Known discrepancies and risks

1. **Docs and code now cover the Flow B feature set, but only in simulation.**
   The RTL performs AUTH_REQ -> HMAC -> AUTH_RESP, periodic signed history,
   READ_HIST, lock after three failed RESULTs, and prefixes 0x41/0x53/0x48; the
   Python model verifies the history (gaps/rollback/truncation). The cocotb
   suite passes 23/23. Do not claim board verification (T6/T7/T9) yet.

2. **MILESTONES says M3 demo is done.**
   That refers to Flow A (MicroBlaze). After the 18 October pivot, Flow A is only
   a fallback. Flow B RTL is built and sim-verified; the Cmod board run and
   KV260 physical tests are still pending (KV260 bitstream is built).

3. **Basys 3 XDC mismatch.**
   `fpga/basys_3/nexys_a7.xdc` contains Nexys pins. The Basys 3 project points
   to a generated `basys_3.xdc`. Create a correct Basys 3 XDC before T5.

4. **Stale cocotb build.**
   Icarus reuses `sim_build/sim.vvp` across targets. `make all` now runs
   `make clean` between targets; a standalone `make <target>` after another
   target still needs an explicit `make clean`.

5. **HMAC message length limit.**
   The RTL wrapper supports ≤ 55 bytes per message. The auth message is 38, so
   it works. Do not push a full history dump through one HMAC call; sign each
   record separately.

6. **Key handling in Flow A.**
   The key is written over AXI from firmware. That is a demo shortcut. The
   target path must use `key_vault`/PUF and remove software access.

7. **KV260 PL clock ownership.**
   `pl_clk0` is configured by the PS boot firmware and Linux, not by the
   bitstream. Stock Kria Ubuntu may leave it at the RPLL default (96.97 MHz) or
   gate it. The RTL UART/I2C timing assumes 100 MHz; verify `pl0_ref` first
   (RUNBOOK §5). `clk_ignore_unused` handles gating; a wrong rate needs a
   BOOT.BIN or a rebuild for the actual clock.

7. **Lock semantics.**
   Firmware `locked` does not block authentication. The station's DB lock is the
   effective mechanism. The target chip-side lock after 3 failures is not
   implemented.

8. **Fixed voltage in Flow A.**
   Flow A has no ADC. Flow B reads the ADS1115 over I2C; the demo's voltage
   changes require Flow B or a proxy/dataset.

9. **PUF is not production-ready.**
   The behavioral model's fuzzy extractor is simplified. The RTL uses
   asynchronous RO counters that are not standard FPGA practice. Present it as
   stage 2.

10. **Symmetric key + online database.**
    The station must reach the server. This is a deliberate, documented
    limitation.

11. **Volatile history.**
    Power loss loses the counter and buffer. The demo's "power cut" Q&A answer
    depends on this; the product needs NVM or a backup supply.

12. **No dashboard/attacker proxy code in the repo yet.**
    `alur-demo.md` assigns these to Budi. The demo cannot run end-to-end
    without them.

---

## 12. Roadmap to demo day

Ordered by critical path.

### Without hardware (can start now)

1. **~~Freeze the history contract.~~** Done 21 Oct: `READ_HIST_REQ/RESP`,
   record layout, prefixes, and verification order are in `model/protocol.py`;
   vectors regenerated and model tests pass 52/52.
2. **~~Add station history verification.~~** Done 21 Oct:
   `Station.verify_history` loads the anchor, checks tags, and detects gaps,
   rollback, and truncation; the web demo renders the health card.
3. **~~Write `rtl/auth_ctrl.v`.~~** Done 21 Oct: frame parser + CRC-8 +
   periodic ADS1115 sampling (1 s) + HMAC + seq counter + signed ring
   buffer + READ_HIST + lock.
4. **~~Write `rtl/uart_if.v`.~~** Done 20 Oct: 115200 8N1, mid-bit sampling.
5. **~~Write `rtl/i2c_master.v` + `rtl/ads1115_ctrl.v`.~~** Done 20 Oct;
   cocotb `make ads1115` passes 2/2. Integrated in `sebatt_top`; Cmod S7
   hardware T9 still pending.
6. **~~Write `rtl/sebatt_top.v`.~~** Done 20 Oct: clk/reset/UART/I2C/LED.
7. **~~Write the cocotb TB for `auth_ctrl`.~~** Done 21 Oct: `make auth`
   passes 12/12 against `model.hmac`/`model.protocol` (auth, lock, STATUS,
   READ_HIST, periodic sampling interval, dump race, switch source, parser
   resync).
8. **~~KV260 prep.~~** Done 21 Oct: Pmod XDC, PS clock-only block design,
   full bitstream + `.bit.bin`, runbook. Physical T6/T7/T9/T10 still pending.

### When a board is available

9. Re-run Fase 0 preflight.
10. If the RTL is not ready, use Flow A to record the fallback video (T1–T4).
11. Build and test the RTL chain (T5–T7).
12. Record the final demo video.

### Before submission

13. Finalize the dashboard and attacker proxy.
14. Rehearse the 60-second demo five times.
15. Write the 2-page README with block diagram, how to run, test results, and
    AI usage.
16. Verify the submitted PDFs and repository contents.

---

## 13. Glossary

| Term | Meaning |
|---|---|
| ADC | Analog-to-Digital Converter; turns voltage into a number |
| ADS1115 | 16-bit I2C ADC used as the external demo voltage source |
| I2C | Two-wire bus (SCL/SDA) used by the ADS1115 |
| AXI4-Lite | Simple memory-mapped bus used by MicroBlaze to reach peripherals |
| BMS | Battery Management System; monitors and protects the pack |
| BRAM | Block RAM inside the FPGA; volatile |
| Challenge-response | Verifier sends a fresh nonce; prover returns a keyed signature |
| CRC8 | 8-bit checksum for frame errors (not security) |
| ECDSA | Asymmetric signature scheme; planned product upgrade |
| HMAC | Keyed hash: `HMAC(K, m) = H((K⊕opad) ‖ H((K⊕ipad) ‖ m))` |
| ipad/opad | `0x36` / `0x5C` padding constants in HMAC |
| KV260 | AMD Kria KV260 board used on demo day |
| Nonce | Number used once; 32 random bytes per authentication |
| PUF | Physical Unclonable Function; chip-unique manufacturing fingerprint |
| Ring buffer | Fixed-size circular history; oldest record overwritten when full |
| RO-PUF | Ring-Oscillator PUF |
| seq | Monotonic sequence number attached to each sample |
| Tag | HMAC output attached to a record |
| WNS | Worst Negative Slack; Vivado timing metric |
| XADC | On-chip ADC available on some Xilinx FPGAs (Nexys A7, not KV260 PMOD) |

---

## Appendix A — Quick reference

### A.1 Constants

| Item | Value |
|---|---|
| Battery ID (demo) | `42 41 54 01` (`BAT\x01`) |
| Key (demo) | `00 01 02 ... 1F` (32 bytes) |
| Default voltage (Flow A) | 3700 mV |
| Demo ADC | ADS1115, I2C addr `0x48` (ADDR→GND), ±4.096 V, 0.125 mV/LSB |
| Voltage mapping (RTL switch test) | `3000 + sw[7:0] * 5` mV |
| Nonce length | 32 bytes |
| HMAC length | 32 bytes |
| Auth message length | 38 bytes (`nonce + ID + V`) |
| History record length | 38 bytes (`seq + V + tag`) |
| History buffer | 64 records |
| UART | 115200, 8N1 |
| Frame overhead | 4 bytes (`CMD + LEN2 + CRC1`) |
| SHA block | 64 bytes, 512 bits |
| SHA rounds | 64 |
| SHA block latency | ~113 cycles |
| HMAC blocks | 4 |
| History storage | 64 × 38 = 2 432 bytes in distributed RAM/registers; 0 Block RAM |

### A.2 Frame examples

`AUTH_REQ` with nonce `00 01 ... 1F`:

```
01 00 20 <32 bytes nonce> <CRC8>
```

`AUTH_RESP` with `BAT\x01`, 3700 mV (`0E 74`), and 32-byte HMAC:

```
02 00 26 42 41 54 01 0E 74 <32 bytes HMAC> <CRC8>
```

### A.3 Status values

```
VALID            0x00
INVALID_HMAC     0x01
REPLAY_DETECTED  0x02
BATTERY_LOCKED   0x03
UNKNOWN_BATTERY  0x04
```

### A.4 HMAC IP address map

```
0x00 CTRL       [0] start, [1] init
0x04 STATUS     [0] done, [1] busy
0x08 MSG_LEN
0x10 KEY[0]  ... 0x2C KEY[7]
0x30 MSG[0]  ... 0x6C MSG[15]
0x70 HASH[0] ... 0x8C HASH[7]
```

### A.5 Commands

```
0x01 AUTH_REQ
0x02 AUTH_RESP
0x03 RESULT
0x04 LOCK
0x05 UNLOCK
0x06 STATUS
0x07 READ_HIST_REQ
0x08 READ_HIST_RESP
```

### A.6 The five things to memorize

1. **Problem:** battery history is reported by software and can be edited.
2. **Mechanism:** sample + monotonic seq + HMAC at the measurement point.
3. **Freshness:** station nonce per swap; DB anchor `last_seq`.
4. **Verification:** recompute HMAC and check contiguous sequence.
5. **Boundary:** the demo ADC is external, the counter is volatile, and the key
   is symmetric; state these limits honestly.
