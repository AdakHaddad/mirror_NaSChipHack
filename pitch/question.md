# Demo Day Q&A — SeBatt

Preparation sheet for the 3-minute Q&A on Demo Day (23 October 2026).
Answers are written to be **spoken**, not read: 2–4 sentences each. When a
judge pushes, use the "If pressed" line and stop.

Rules: never answer a question you are not sure about with a guessed number.
Say "we have not measured that yet" and name the next step. Honesty about
limits reads as competence; a wrong number destroys trust.

## Who answers what

| Topic | Lead |
|---|---|
| Problem, demo story, market, business | Guntur |
| RTL, FPGA, protocol, security architecture | Muqtada |
| Station software, dashboard, test data | Budi |

## 1. Core questions (the 60-second version)

**Q: What is SeBatt?**
A: A silicon root of trust for battery packs. It samples the cell voltage
itself, signs every sample with a monotonic sequence number using HMAC-SHA-256
in hardware, and lets the swap station verify that the history was not edited,
deleted, or rolled back.

**Q: What problem does it solve?**
A: Battery history today is protected by passwords and lives in firmware that
can be reflashed. A modified BMS can hide deep discharge or rewrite cycle
counts to win a warranty claim or raise a used battery's price. SeBatt makes
that history tamper-evident at the point of measurement.

**Q: How does it work, in one breath?**
A: ADC → control logic → HMAC → UART, all inside the FPGA; no CPU touches the
sample. The station sends a fresh 32-byte nonce, reads the signed history, and
checks the summary tag, the sequence continuity, and the anchor it stored last
time.

**Q: What is new compared with existing battery gauges?**
A: Gauges such as TI's BQ40Z50 authenticate the pack's identity, but their
lifetime log is password-protected and resettable; secure elements such as the
DS28E38 prove identity only. We sign each measurement with a sequence and
verify the log outside the pack. We have not found a commercial product that
signs per-sample history; this is a product scan, not a patent clearance.

**Q: Is the demo real or simulated?**
A: The RTL, ADC sampling, HMAC, sequence counter, and lock logic run on a real
Kria KV260; the station and dashboard are Python on a laptop. The ADS1115 is
external in the PoC; in the target ASIC the ADC is on the same die as the
signing logic.

**Q: Where are you today?**
A: A working PoC verified on the KV260 on 21 October: authentication, signed
history, and tamper, delete, cut, and replay attacks all rejected on the board.
No field pilot yet; that is the next step.

## 2. Technical questions

**Q: Why HMAC-SHA-256 and not ECDSA?**
A: In a closed swap ecosystem the operator already provisions the keys on both
sides, so a symmetric MAC is smaller, faster, and simpler than a signature
scheme; the core takes 113 cycles per SHA-256 block, about 452 cycles for a
full authentication message. An ECDSA variant with a
per-chip keypair and certificate is possible when public verifiability is
needed; we documented that path.

**Q: What exactly is signed?**
A: Each record carries `seq`, voltage, and an HMAC tag with a domain-separation
prefix (`0x53`). Authentication signs `nonce || ID || voltage` (`0x41`). The
dump ends with a summary tag (`0x48`) over the fresh nonce and the sequence
range, so a stale dump cannot be passed off as fresh.

**Q: Why the sequence number and the anchor?**
A: The sequence gives order and continuity. The station remembers the last
sequence it accepted (the anchor) and refuses anything older, so deleting
records, cutting the newest ones, or replaying an old dump all fail
verification.

**Q: What does the station actually check?**
A: Recompute the summary tag with the fresh nonce (catches replay), compare the
last sequence to the anchor (catches rollback), verify continuity (catches
gaps), and recompute every record tag (catches edits). Any failure is reported
back to the chip; three consecutive failures lock it.

**Q: Why is HISTORY_TRUNCATED accepted then?**
A: The 64-record buffer is a ring: old records legitimately fall off when it
fills. Truncation from the front is reported and accepted as normal aging; a
gap in the middle or a rollback is rejected. The guarantee is on the retained
window, and the station is told when that window moved.

**Q: How is the key provisioned?**
A: In the demo, stage 1 uses a fixed key provisioned into the bitstream and the
station database for reproducibility. The production design derives a per-chip
key from the RO-PUF, reconstructed on the fly and never stored, with an
HSM/KMS holding wrapped material and anchors. The fixed-key demo is a
functional PoC, not a claim of production key security.

**Q: What happens if power is cut?**
A: The demo counter is volatile: power loss resets the sequence to 0 and the
station rejects the battery as a rollback. That is fail-safe, not fail-open,
but a product needs a non-volatile monotonic counter. We list this as a known
limitation.

**Q: Your HMAC target was 300 cycles; you say 452. Why?**
A: The proposal target assumed a more parallel SHA-256 datapath. The current
core is an iterative single-round design: 113 cycles per block × 4 blocks,
about 452 cycles. We report the miss honestly; end-to-end authentication still
measures 13.7 ms average and 73 authentications per second, above the
50-per-second requirement. Next step is unrolling/pipelining.

**Q: The ADC is external — isn't that a weak point?**
A: Yes, in the PoC: the ADS1115 is a separate chip on I2C, so the analog
boundary is outside the trust perimeter. The ASIC target integrates the ADC on
the same die as the signing logic. We say this on stage; we do not claim the
PoC protects the analog line.

**Q: What if the I2C line is cut or shorted?**
A: The board test found that a shorted SDA could read 0 mV and be signed as if
real. The RTL now starts a transaction only when SDA and SCL are both high and
reports an error otherwise; that fix is in the latest build and is being
re-verified. In the ASIC, the on-die ADC removes this bus from the threat
surface.

**Q: How much history, and how often?**
A: A 64-record signed ring buffer, sampled every second in the PoC; the demo
maps one point to about 3 hours of use, so 64 points cover about 8 days. The
production interval is a profile setting. Longer retention is a bigger buffer
or signed checkpoints to external storage; the protocol does not change.

**Q: Why not blockchain?**
A: A nonce challenge plus a station-side anchor already gives tamper-evidence
without consensus, miners, or network dependency; a swap station must work
offline. The signed, chained history is compatible with an append-only audit
log if an operator wants multi-party verification later.

**Q: Why FPGA now and ASIC later?**
A: An FPGA proves the RTL on real silicon fabric with real timing at low cost
and lets us iterate during the hackathon. An ASIC is needed for unit cost,
on-die ADC, PUF, and a non-volatile counter. Our MPW path is chipIgnite on
SKY130 at about USD 14,950 per shuttle; the timeline depends on funding.

**Q: What about side-channel and fault-injection attacks?**
A: Out of scope for the PoC. HMAC is a standard symmetric construction, but a
production secure IC needs SCA/FI evaluation, shielding, and likely a
certification program. We do not claim resistance we have not measured.

**Q: Is HMAC-SHA-256 post-quantum safe?**
A: HMAC-SHA-256 is symmetric; Grover's algorithm gives at most a quadratic
speedup, so a 256-bit key still targets roughly 128-bit security. Unlike ECDSA,
it does not need a post-quantum migration for signatures.

## 3. Security and threat model

**Q: What exactly are you defending against?**
A: A compromised BMS, owner, or intermediary that edits, deletes, truncates, or
replays the usage history before it reaches the station. The pack-side data
path is the threat surface; the operator's station is the verifier.

**Q: Can I clone the chip?**
A: Not in the target design: the key comes from the RO-PUF, which is
physically unclonable, and never leaves the die. In the demo the key is fixed,
so the demo is cloneable — that is exactly why stage 2 exists and why we state
it openly.

**Q: Can I replay an old history?**
A: No. The station sends a new 32-byte nonce every swap; the summary tag covers
that nonce, so an old dump fails as INVALID_HMAC. This was tested on the board.

**Q: Can I swap in a whole different battery?**
A: The chip proves identity and history, not ownership. If a battery is
reported stolen, the operator marks it in the database and the station returns
BATTERY_LOCKED; the chip also has a local lock after three consecutive failed
results. Policy stays with the operator.

**Q: What if the operator is malicious?**
A: The station is the verifier and anchor, so a fully colluding operator can
accept anything — that is outside the model; the chip protects against
pack-side manipulation. The design assumes the operator wants the truth about
its own fleet, which is the commercial case.

**Q: What if the station database is stolen?**
A: In stage 1 the database holds the shared key, so its compromise would allow
forged history; that is why production moves keys into an HSM/KMS and migrates
to per-chip derivation or the ECDSA variant where the verifier only needs
public data. We list database hardening as a productization task, not a solved
problem.

**Q: Why not just add a secure element next to the gauge?**
A: A secure element can prove identity, but the gauge's log is still written by
firmware. Our logic signs the measurement inside the same silicon that samples
it, and chains records with a sequence the verifier anchors. You could
integrate that logic into a gauge — that is our licensing path, not a
contradiction.

**Q: Does SeBatt replace the BMS?**
A: No. The BMS keeps doing protection, balancing, and SoC estimation. SeBatt
adds an independent, signed measurement and history channel that the BMS cannot
rewrite. In the ASIC it can share the pack's sensors.

## 4. Demo-specific questions

**Q: Is the attack staged?**
A: The attack is real on the data: we pull a genuine signed dump from the chip,
modify or delete records in host memory (or through an optional interposer
laptop), and run the same verification the station runs at a swap. The failure
is the chip's signature check, not a scripted banner.

**Q: Why does the demo take place on a laptop?**
A: The laptop plays the station role because the KV260 is the battery-side chip
in this setup. In the field the station is the swap cabinet's controller; the
verification code is the same Python model we ship in the repo.

**Q: Show me replay and lock.**
A: `attack replay` reuses a dump for an old nonce and is rejected as
INVALID_HMAC; `lock` makes authentication return BATTERY_LOCKED, and `unlock`
restores it. Automatic locking after three failed results is verified in
simulation but not yet demonstrated on the board — say so if asked.

**Q: What if the board fails on stage?**
A: We switch to the recorded demo without apologizing and keep the narrative.
The same scenarios were verified on the board on 21 October; the video is the
fallback, not the plan.

**Q: Why is the displayed voltage scaled?**
A: The potentiometer represents one Li-ion cell: 0–3.3 V at the pin maps to
0–4.2 V on screen. Production profiles for a 3S LiPo pack and a 12 V lead-acid
battery use resistor dividers and are already in the station software.

## 5. Business questions

**Q: How big is the market?**
A: Bottom-up: about 2,200 swap stations across SWAP (1,500+), Electrum (400+),
and Volta (300+); at 8–10 battery slots per rack that is roughly 20,000
batteries installed today. Indonesia had 541,678 electric vehicles by August
2026 — 196,051 of them electric motorcycles in June 2025 — and the government
target is 13 million electric motorcycles by 2030. V-Green alone reports 2,000+
swap points.

**Q: Who pays, and how much?**
A: Three streams: IP license to gauge/BMS makers (USD 50–100k upfront plus 1–2%
of chip price, benchmarked to ARM-style licensing), a retrofit module for
fleets (USD 3.50 per unit at about 55% gross margin), and a verification
service for operators (Rp 5,000–10,000 per battery per year, roughly 0.3–1% of
the Rp 1.0–2.4 million annual subscription).

**Q: Why would an operator pay that?**
A: One prevented incident is worth Rp 2–4 million — a pack is Rp 4.55 million
(VinFast), roughly half a motorcycle's price. At a 1–2% annual incidence
assumption, 2,000 batteries represent Rp 40–160 million of value a year; our
fee captures roughly 10–20% of the midpoint. The incidence assumption is
anchored on DOE/Recurrent replacement data and Geotab degradation data, and
must be confirmed with operators.

**Q: What is your moat?**
A: The combination of sampling and signing in one silicon path, sequence-
anchored verification outside the pack, and the integration into a station
workflow. We have not filed patents; we ran a product scan, not a patent
clearance. Execution and operator integration are the real moat at this stage.

**Q: What traction do you have?**
A: A board-verified PoC and a documented protocol; no paying customer yet. The
next milestone is a paid pilot with one operator on 2,000–5,000 batteries — one
city cluster — which is a reference, not our revenue plan.

**Q: How much money do you need?**
A: The next hard cost is an MPW shuttle at about USD 14,950, plus EDA and
engineering time. We are pursuing non-dilutive grants and a paid pilot first;
we are not pitching a VC round at this stage.

**Q: Are you a startup or a research project?**
A: We pitch as a deep-tech startup because the problem and the customer are
real. Execution is staged: Demo Day, then a paid pilot, then MPW, then
spin-off or licensing. If the team does not commit full-time and no operator
pays, the honest outcome is a research project with a licensing path.

**Q: Why Indonesia?**
A: It is the world's largest two-wheeler market, swap networks are scaling
here, and the gauge/BMS supply chain is local. A solution proven on Indonesian
fleets travels to Southeast Asia; a generic chip vendor will not optimize for
this workflow.

## 6. Team and risk

**Q: Can three students deliver this?**
A: We already delivered a working RTL stack on a real board, a verified
protocol, and a station/dashboard in a hackathon timeline. The gap to product
is silicon and certification, which is why the plan is partnership and
licensing rather than building a fabless company alone.

**Q: What is the biggest risk?**
A: Adoption and silicon cost. Operators must see value in a paid pilot, and an
ASIC needs funding before revenue. Mitigation: retrofit module and IP licensing
first, non-dilutive funding for MPW, and an honest staged plan.

**Q: What is the timeline?**
A: 2026: PoC and pilot conversations. 2027: paid pilot with one operator and an
MPW shuttle if funding lands. 2028+: productization or licensing, depending on
pilot results.

## 7. Trap questions — quick answers

| Question | Answer |
|---|---|
| "Isn't this just DRM for batteries?" | It is an audit trail the owner and operator can verify; the battery owner benefits from a truthful resale value. |
| "Why not put this in the cloud?" | The cloud cannot vouch for a measurement it did not take; signing must happen at the sensor. The cloud only stores anchors. |
| "Your demo tampers on the laptop — trivial." | That is the threat model: a compromised host between pack and station. The cryptographic check is identical wherever the bytes are altered. |
| "Only voltage? SoC, current, temperature matter." | Voltage is the demo signal; the signing path generalizes. The contribution is the integrity chain, not the sensing modality. |
| "Your key is in the bitstream." | True for the stage-1 demo. Stage 2 derives it from the RO-PUF per chip and never stores it. |
| "64 records is tiny." | It is a ring buffer with a verifier-side anchor; truncation is explicit and gaps/rollback are rejected. Retention can grow without changing the protocol. |
| "What if the BMS stops the chip sampling?" | The chip samples autonomously; missing records are visible as no new entries and a red LED. In the ASIC the sampling clock is independent of the BMS. |
| "Why should we trust your measurements?" | Calibration and on-die ADC are productization work; the PoC demonstrates integrity, not metrology-grade accuracy. We do not overclaim. |
| "You exceed your own 5,000 LUT target." | The core on the Cmod S7 is about 4,400 LUT and meets it; the KV260 full build adds the I2C master, LED logic, and board glue, totaling 5,607 LUT. We report both instead of hiding the larger build. |

## 8. Do not say

- "The PUF is in the demo." It is modeled (`model/ro_puf.py`) but not in the
  bitstream; the demo uses a fixed key.
- "Production-ready" or "certified." No security certification yet; only
  FIPS 180-4 / RFC 4231 algorithm vectors pass in simulation.
- "Eliminates fraud." It makes history tamper-evident; policy and sensors
  still matter.
- TAM "USD 1.8 billion" or CAGR "24.5%". Unsourced; use the bottom-up numbers.
- Royalty "USD 0.25–0.50 per chip". Off-benchmark; use 1–2% of chip price.
- "No one has done this." Say "we have not found a commercial product."
- "1,000 trials per scenario." Not run; say 86 Python tests, 26 RTL
  simulation tests, and the board attack tests.

## 9. Numbers cheat sheet

| Metric | Value | Note |
|---|---|---|
| End-to-end authentication | 13.7 ms average (50 runs), 14.2–14.7 ms single | Measured on KV260, 21 Oct |
| Throughput | 73.1 authentications/s (50/50 VALID) | Target ≥ 50/s |
| READ_HIST, 64 records | 292.5 ms | Includes 65 tag verifications |
| HMAC core | ~452 cycles (113/block × 4) | Above the 300-cycle proposal target |
| KV260 build | WNS +0.749 ns @ 100 MHz, 5,607 LUT, 6,207 FF | Latest build; board re-test pending |
| Tests | 86 Python, 26 RTL (cocotb) | Plus board attack tests |
| History | 64 signed records, 32-bit sequence | 3 consecutive failures → lock |
| Attacks rejected on board | tamper, delete, cut, replay | VALID on unmodified dumps |
| Installed base estimate | ~20,000 batteries | 2,200 stations × 8–10 slots |
| Pack value | Rp 4.55 million (VinFast) | Loss per case Rp 2–4 million |
| Incidence assumption | 1–2% per year | Anchored on DOE/Recurrent + Geotab; verify with operators |
| Pricing | License USD 50–100k; royalty 1–2% of chip price; module USD 3.50 (~55% GM); service Rp 5–10k/battery/year | Sources in `bisnis/pitch-dan-angka.md` |
| MPW | USD 14,950 per shuttle | chipIgnite (ChipFoundry), SKY130 |

## 10. If the live demo misbehaves

- Board silent for 10 seconds: Budi switches to the recorded demo; Guntur
  continues the same script without apologizing.
- ADC unreadable: switch the dashboard to dataset mode and say "input from
  recorded data".
- Projector fails: turn the station laptop toward the judges and enlarge the
  dashboard.
- Judge asks something we do not know: "We have not measured that yet; here is
  how we would." Then name the next step.

## 11. Sources

Internal: [hasil uji KV260](../docs/catatan-teknis/hasil-uji-kv260.md),
[spesifikasi](../docs/catatan-teknis/spesifikasi.md),
[alur teknis](../docs/catatan-teknis/alur-teknis.md),
[pembanding produk](catatan-pembanding.md),
[angka bisnis](../bisnis/pitch-dan-angka.md),
[naskah pitch](pitch_deck.md).

External (competitors and benchmarks): [TI BQ40Z50-R5 TRM](https://www.ti.com/lit/ug/sluucn4b/sluucn4b.pdf),
[ADI ADRF8800/8850](https://www.analog.com/media/en/technical-documentation/data-sheets/adrf8800-8850.pdf),
[Infineon OPTIGA Authenticate](https://www.infineon.com/cms/de/product/security-smart-card-solutions/optiga-embedded-security-solutions/optiga-authenticate/optiga-authenticate-on/),
[DOE/Recurrent battery replacement](https://www.energy.gov/cmei/vehicles/articles/fotw-1339-april-22-2024-plug-electric-vehicle-battery-replacements-due),
[Geotab degradation 2026](https://www.globenewswire.com/news-release/2026/01/13/3218328/0/en/Updated-analysis-finds-average-battery-degradation-of-2-3-per-year-with-charging-behaviour-emerging-as-a-key-driver.html).
