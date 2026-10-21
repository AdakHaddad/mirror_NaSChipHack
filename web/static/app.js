(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const el = {
    banner: $("result-banner"),
    kicker: $("result-kicker"),
    title: $("result-title"),
    message: $("result-message"),
    statSeq: $("stat-seq"),
    statPending: $("stat-pending"),
    statFail: $("stat-fail"),
    batteryId: $("battery-id"),
    modePill: $("mode-pill"),
    modeLabel: $("mode-label"),
    chart: $("chart"),
    chartNote: $("chart-note"),
    chartSub: $("chart-sub"),
    healthCard: $("health-card"),
    healthId: $("health-id"),
    healthBadge: $("health-badge"),
    healthCycles: $("health-cycles"),
    healthDeep: $("health-deep"),
    healthMin: $("health-min"),
    healthMax: $("health-max"),
    healthSamples: $("health-samples"),
    healthPending: $("health-pending"),
    healthNote: $("health-note"),
    voltageValue: $("voltage-value"),
    voltageControl: $("voltage-control"),
    voltageHint: $("voltage-hint"),
    slider: $("voltage-slider"),
    btnSwap: $("btn-swap"),
    btnRecord: $("btn-record"),
    autoRecord: $("auto-record"),
    autoRow: $("auto-row"),
    autoState: $("auto-state"),
    actionHint: $("action-hint"),
    recordsCount: $("records-count"),
    seqPill: $("seq-pill"),
    recordsBody: $("records-body"),
    recordsEmpty: $("records-empty"),
    btnDelete: $("btn-delete"),
    btnTamper: $("btn-tamper"),
    btnRestore: $("btn-restore"),
    attackTitle: $("attack-title"),
    attackCopy: $("attack-copy"),
    attackHint: $("attack-hint"),
    btnUnlock: $("btn-unlock"),
    btnPowerCycle: $("btn-power-cycle"),
    btnReset: $("btn-reset"),
    logList: $("log-list"),
    toast: $("toast"),
    footerSource: $("footer-source"),
    footerHint: $("footer-hint"),
  };

  const app = {
    data: null,
    busy: false,
    polling: false,
    auto: false,
    autoTimer: null,
    offline: false,
    toastTimer: null,
    signature: null,
  };

  const fmtInt = new Intl.NumberFormat("id-ID");
  const fmtDecimal = new Intl.NumberFormat("id-ID", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  function fmtV(mv) {
    if (!Number.isFinite(mv)) return "—";
    return `${fmtDecimal.format(mv / 1000)} V`;
  }

  function fmtVoltageShort(mv) {
    return (mv / 1000).toFixed(1).replace(".", ",");
  }

  function fmtTime(epoch) {
    if (!epoch) return "";
    return new Date(epoch * 1000).toLocaleTimeString("id-ID", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function showToast(message, isError = false) {
    el.toast.textContent = message;
    el.toast.classList.toggle("error", isError);
    el.toast.classList.add("show");
    clearTimeout(app.toastTimer);
    app.toastTimer = setTimeout(() => el.toast.classList.remove("show"), 3600);
  }

  function isFpga() {
    return app.data?.mode === "fpga";
  }

  function syncModePill() {
    const fpga = isFpga();
    const error = fpga && app.data?.hardware?.connected === false;
    el.modePill.classList.toggle("offline", app.offline);
    el.modePill.classList.toggle("fpga", fpga);
    el.modePill.classList.toggle("warn", Boolean(error) && !app.offline);
    if (app.offline) {
      el.modeLabel.textContent = "Server offline";
    } else if (fpga) {
      const port = app.data?.hardware?.port || "UART";
      el.modeLabel.textContent = error ? `FPGA · ${port} (gangguan)` : `FPGA · ${port}`;
    } else {
      el.modeLabel.textContent = "Model Python, bukan FPGA";
    }
  }

  function setOffline(offline) {
    app.offline = offline;
    syncModePill();
  }

  function setBusy(busy) {
    app.busy = busy;
    renderControls();
  }

  async function request(path, body = {}) {
    if (app.busy) return null;
    setBusy(true);
    try {
      const options = { method: "POST", cache: "no-store" };
      options.headers = { "Content-Type": "application/json" };
      options.body = JSON.stringify(body);
      const response = await fetch(path, options);
      const payload = await response.json().catch(() => ({}));
      if (payload.state) apply(payload.state);
      if (!response.ok || payload.ok === false) {
        showToast(payload.message || "Permintaan gagal.", true);
        return null;
      }
      setOffline(false);
      return payload;
    } catch {
      setOffline(true);
      showToast("Tidak dapat menghubungi server.", true);
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function fetchState() {
    if (app.polling || app.busy) return;
    app.polling = true;
    try {
      const response = await fetch("/api/state", { cache: "no-store" });
      if (!response.ok) throw new Error("state unavailable");
      const data = await response.json();
      apply(data);
      setOffline(false);
    } catch {
      setOffline(true);
    } finally {
      app.polling = false;
    }
  }

  function currentMv() {
    return Number(el.slider.value);
  }

  function updateVoltageLabel() {
    el.voltageValue.textContent = fmtDecimal.format(currentMv() / 1000);
  }

  function setVoltage(mv) {
    el.slider.value = String(mv);
    updateVoltageLabel();
  }

  function apply(data) {
    if (!data || typeof data !== "object") return;
    app.data = data;
    const signature = JSON.stringify(data);
    if (signature === app.signature) return;
    app.signature = signature;
    render();
  }

  function render() {
    const data = app.data;
    if (!data) return;
    renderBanner(data);
    renderChart(data);
    renderHealth(data);
    renderRecords(data);
    renderLogs(data);
    renderControls();
    syncModePill();
    if (data.mode === "fpga" && Number.isFinite(data.voltage_mv)) {
      el.voltageValue.textContent = fmtDecimal.format(data.voltage_mv / 1000);
    } else {
      updateVoltageLabel();
    }
    el.batteryId.textContent = data.battery?.id || "BAT-0001";
    el.healthId.textContent = data.battery?.id || "BAT-0001";
  }

  function renderBanner(data) {
    const locked = Boolean(data.battery?.locked);
    const result = data.last_result;
    let status = "idle";
    let kicker = "Stasiun penukaran";
    let title = "SIAP";
    let message = "Tekan “Tukar baterai” untuk memverifikasi riwayat tegangan paket.";

    if (result) {
      if (result.status === "accepted") {
        status = "accepted";
        kicker = "Hasil penukaran";
        title = "DITERIMA";
      } else {
        status = locked ? "locked" : "rejected";
        kicker = locked ? "Chip terkunci" : "Hasil penukaran";
        title = "DITOLAK";
      }
      message = result.message;
      if (result.at) kicker += ` · ${fmtTime(result.at)}`;
    } else if (locked) {
      status = "locked";
      kicker = "Chip terkunci";
      title = "TERKUNCI";
      message = "Chip tidak merespons. Buka kunci untuk melanjutkan demo.";
    }

    el.banner.dataset.status = status;
    el.kicker.textContent = kicker;
    el.title.textContent = title;
    el.message.textContent = message;
    el.statSeq.textContent = fmtInt.format(data.last_seq || 0);
    el.statPending.textContent = fmtInt.format(data.pending || 0);
    el.statFail.innerHTML = `${fmtInt.format(data.fail_streak || 0)}<span class="muted">/3</span>`;
  }

  function renderChart(data) {
    const records = Array.isArray(data.records)
      ? [...data.records].sort((a, b) => a.seq - b.seq)
      : [];
    const width = Math.max(300, Math.round(el.chart.clientWidth || 800));
    const narrow = width < 560;
    const height = narrow ? 300 : 340;
    const margin = { left: narrow ? 40 : 48, right: narrow ? 12 : 18, top: 18, bottom: 34 };
    const plotW = width - margin.left - margin.right;
    const plotH = height - margin.top - margin.bottom;
    const yMin = 1900;
    const yMax = 4300;

    const y = (mv) => margin.top + ((yMax - mv) / (yMax - yMin)) * plotH;

    if (!records.length) {
      el.chart.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Belum ada riwayat tegangan">
          <rect x="${margin.left}" y="${margin.top}" width="${plotW}" height="${plotH}" rx="10" fill="rgba(148,163,184,0.025)"></rect>
          <text x="${width / 2}" y="${height / 2 - 8}" text-anchor="middle" class="empty-chart">Belum ada catatan tegangan.</text>
          <text x="${width / 2}" y="${height / 2 + 15}" text-anchor="middle" class="empty-chart">${data.mode === "fpga" ? "Tekan “Muat riwayat” setelah FPGA sampling." : "Catat sampel untuk memulai riwayat."}</text>
        </svg>`;
      if (data.mode === "fpga" && data.hardware?.error) {
        el.chartNote.textContent = "FPGA belum merespons";
      } else {
        el.chartNote.textContent = data.power_cycled
          ? "Daya dicabut: riwayat hilang, penghitung kembali ke 0"
          : "Menunggu verifikasi";
      }
      return;
    }

    const firstSeq = records[0].seq;
    const lastSeq = Math.max(data.chip_seq || records[records.length - 1].seq, firstSeq);
    const span = Math.max(1, lastSeq - firstSeq);
    const x = (seq) =>
      margin.left + ((seq - firstSeq) / span) * plotW;

    const yTicks = [2000, 2500, 3000, 3500, 4000, 4200];
    const grid = yTicks
      .map((mv) => {
        const py = y(mv);
        return `
          <line x1="${margin.left}" y1="${py}" x2="${width - margin.right}" y2="${py}" class="grid-line"></line>
          <text x="${margin.left - 9}" y="${py + 3}" text-anchor="end" class="axis-text">${fmtVoltageShort(mv)}</text>`;
      })
      .join("");

    const tickCount = narrow ? 4 : 6;
    const xTicks = [];
    const seenTicks = new Set();
    for (let i = 0; i < tickCount; i += 1) {
      const seq = Math.round(firstSeq + (span * i) / (tickCount - 1));
      if (!seenTicks.has(seq)) {
        seenTicks.add(seq);
        xTicks.push(seq);
      }
    }
    const xAxis = xTicks
      .map((seq) => {
        const px = x(seq);
        return `
          <line x1="${px}" y1="${margin.top + plotH}" x2="${px}" y2="${margin.top + plotH + 4}" class="grid-line"></line>
          <text x="${px}" y="${height - 12}" text-anchor="middle" class="axis-text">${seq}</text>`;
      })
      .join("");

    const segments = [];
    for (let i = 1; i < records.length; i += 1) {
      const previous = records[i - 1];
      const record = records[i];
      if (previous.deleted || record.deleted) continue;
      if (record.seq !== previous.seq + 1) continue;
      const tampered = previous.tampered || record.tampered;
      segments.push(
        `<line x1="${x(previous.seq)}" y1="${y(previous.mv)}" x2="${x(record.seq)}" y2="${y(record.mv)}" class="trace${tampered ? " tampered" : ""}"></line>`
      );
    }

    const points = records
      .map((record) => {
        const px = x(record.seq);
        const py = y(record.mv);
        const title = `<title>Seq ${record.seq}: ${fmtV(record.mv)}${record.tampered ? ` (asli ${fmtV(record.original_mv)})` : ""}${record.deleted ? " — dihapus" : ""}</title>`;
        if (record.deleted) {
          return `<circle cx="${px}" cy="${py}" r="4.5" class="point deleted">${title}</circle>`;
        }
        if (record.tampered) {
          const ghost = y(record.original_mv);
          return `
            <line x1="${px}" y1="${ghost}" x2="${px}" y2="${py}" class="tamper-arrow"></line>
            <circle cx="${px}" cy="${ghost}" r="5" class="ghost"></circle>
            <circle cx="${px}" cy="${py}" r="5.5" class="point tampered">${title}</circle>`;
        }
        return `<circle cx="${px}" cy="${py}" r="4.5" class="point ${record.mv < 2500 ? "deep" : "safe"}">${title}</circle>`;
      })
      .join("");

    el.chart.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Grafik riwayat tegangan baterai">
        <rect x="${margin.left}" y="${y(4200)}" width="${plotW}" height="${y(2500) - y(4200)}" class="zone-safe"></rect>
        <rect x="${margin.left}" y="${y(2500)}" width="${plotW}" height="${y(2000) - y(2500)}" class="zone-danger"></rect>
        <rect x="${margin.left}" y="${y(4300)}" width="${plotW}" height="${y(4200) - y(4300)}" class="zone-danger"></rect>
        ${grid}
        ${xAxis}
        <line x1="${margin.left}" y1="${y(2500)}" x2="${width - margin.right}" y2="${y(2500)}" class="limit-line"></line>
        <line x1="${margin.left}" y1="${y(4200)}" x2="${width - margin.right}" y2="${y(4200)}" class="limit-line"></line>
        <text x="${width - margin.right - 4}" y="${y(2500) - 6}" text-anchor="end" class="limit-text">2,5 V</text>
        <text x="${width - margin.right - 4}" y="${y(4200) - 6}" text-anchor="end" class="limit-text">4,2 V</text>
        ${segments.join("")}
        ${points}
      </svg>`;

    const pendingText = data.pending > 0 ? ` · ${data.pending} catatan baru` : "";
    if (data.mode === "fpga" && data.hardware?.error) {
      el.chartNote.textContent = `FPGA: ${data.hardware.error}`;
    } else if (data.power_cycled) {
      el.chartNote.textContent = "Daya dicabut: penghitung kembali ke 0";
    } else if (data.last_result?.status === "rejected") {
      el.chartNote.textContent = `Verifikasi gagal${pendingText}`;
    } else if (data.last_result?.status === "accepted" && data.pending > 0) {
      el.chartNote.textContent = `${data.pending} catatan baru menunggu verifikasi`;
    } else if (data.last_result?.status === "accepted") {
      el.chartNote.textContent = "Riwayat terverifikasi";
    } else if (data.pending > 0) {
      el.chartNote.textContent = `${data.pending} catatan baru menunggu verifikasi`;
    } else {
      el.chartNote.textContent = "Menunggu verifikasi";
    }
  }

  function renderHealth(data) {
    const health = data.health;
    const status = data.health_status || "unverified";
    const locked = Boolean(data.battery?.locked);
    const trusted = status === "trusted" && health;

    el.healthCard.dataset.status = locked ? "untrusted" : status;

    if (locked) {
      el.healthBadge.textContent = "CHIP TERKUNCI";
    } else if (status === "trusted") {
      el.healthBadge.textContent = "TERVERIFIKASI";
    } else if (status === "untrusted") {
      el.healthBadge.textContent = "TIDAK VALID";
    } else {
      el.healthBadge.textContent = "BELUM DIVERIFIKASI";
    }

    el.healthCycles.textContent = trusted ? fmtInt.format(health.cycles) : "—";
    el.healthDeep.textContent = trusted ? fmtInt.format(health.deep) : "—";
    el.healthMin.textContent = trusted ? fmtV(health.min_mv) : "—";
    el.healthMax.textContent = trusted ? fmtV(health.max_mv) : "—";
    el.healthSamples.textContent = trusted
      ? `${fmtInt.format(health.samples)} catatan`
      : "0 catatan";

    if (data.pending > 0 && trusted) {
      el.healthPending.textContent = `+${fmtInt.format(data.pending)} baru`;
    } else if (trusted) {
      el.healthPending.textContent = "riwayat sinkron";
    } else {
      el.healthPending.textContent = "";
    }

    if (locked) {
      el.healthNote.textContent = "Chip terkunci. Buka kunci untuk mengulang skenario demo.";
    } else if (status === "untrusted") {
      el.healthNote.textContent = "Riwayat tidak dapat dipercaya. Kesehatan baterai tidak ditampilkan.";
    } else if (trusted && data.pending > 0) {
      el.healthNote.textContent = `Dihitung dari riwayat terverifikasi hingga seq ${health.verified_seq}; catatan baru belum masuk.`;
    } else if (trusted) {
      el.healthNote.textContent = `Dihitung dari ${fmtInt.format(health.samples)} catatan terverifikasi hingga seq ${health.verified_seq}.`;
    } else if (status === "trusted") {
      el.healthNote.textContent = "Tidak ada catatan pada chip.";
    } else if (data.power_cycled) {
      el.healthNote.textContent = "Daya dicabut: riwayat hilang dan penghitung kembali ke awal.";
    } else {
      el.healthNote.textContent = "Angka muncul setelah riwayat dinyatakan valid.";
    }
  }

  function renderRecords(data) {
    const records = Array.isArray(data.records) ? data.records : [];
    const shown = records.slice(-10).reverse();

    el.recordsCount.textContent = `${fmtInt.format(records.length)} catatan · buffer ${fmtInt.format(data.buffer_size || 64)}`;
    el.seqPill.textContent = `chip ${data.chip_seq || 0} · db ${data.last_seq || 0}`;

    if (!shown.length) {
      el.recordsBody.innerHTML = "";
      el.recordsBody.hidden = true;
      el.recordsEmpty.hidden = false;
      el.recordsEmpty.textContent = data.mode === "fpga"
        ? "Belum ada catatan dari FPGA. Tekan “Muat riwayat”."
        : "Belum ada catatan. Tekan “Catat sampel”.";
      return;
    }

    el.recordsBody.hidden = false;
    el.recordsEmpty.hidden = true;
    el.recordsBody.innerHTML = shown
      .map((record) => {
        const classes = [];
        if (record.deleted) classes.push("deleted");
        if (record.tampered) classes.push("tampered");
        let status = `<span class="status-pill ok">sah</span>`;
        if (record.deleted) status = `<span class="status-pill gone">dihapus</span>`;
        else if (record.tampered) status = `<span class="status-pill bad">diubah</span>`;
        const edit = record.tampered
          ? `<span class="voltage-edit">asli ${fmtV(record.original_mv)}</span>`
          : "";
        return `
          <tr class="${classes.join(" ")}">
            <td class="seq">#${String(record.seq).padStart(2, "0")}</td>
            <td class="voltage">${fmtV(record.mv)}${edit}</td>
            <td class="mono">${escapeHtml(record.tag)}…</td>
            <td>${status}</td>
          </tr>`;
      })
      .join("");
  }

  function renderLogs(data) {
    const logs = Array.isArray(data.logs) ? [...data.logs].reverse() : [];
    if (!logs.length) {
      el.logList.innerHTML = `<div class="empty">Belum ada pemeriksaan.</div>`;
      return;
    }
    el.logList.innerHTML = logs
      .map((log) => {
        const ok = log.status === "accepted";
        return `
          <div class="log-item">
            <span class="log-time">${fmtTime(log.at)}</span>
            <span class="log-badge ${ok ? "ok" : "bad"}">${ok ? "DITERIMA" : "DITOLAK"}</span>
            <span class="log-message">${escapeHtml(log.message)}</span>
          </div>`;
      })
      .join("");
  }

  function renderControls() {
    const data = app.data;
    if (!data) return;

    const fpga = data.mode === "fpga";
    const locked = Boolean(data.battery?.locked);
    const baseline = (data.last_seq || 0) > 0
      || data.health_status === "trusted"
      || data.health_status === "untrusted";
    const records = Array.isArray(data.records) ? data.records : [];
    const newRecords = baseline
      ? records.filter((record) => record.seq > data.last_seq && !record.deleted)
      : [];
    const hasNew = newRecords.length > 0;
    const hasTamperable = newRecords.some((record) => !record.tampered);
    const hasDamage = records.some((record) => record.deleted || record.tampered);

    el.btnSwap.disabled = app.busy;
    el.btnRecord.disabled = app.busy;
    el.btnRecord.textContent = fpga ? "Muat riwayat" : "Catat sampel";
    el.btnDelete.disabled = app.busy || locked || !hasNew;
    el.btnTamper.disabled = app.busy || locked || !hasTamperable;
    el.btnRestore.disabled = app.busy || !hasDamage;
    el.btnUnlock.hidden = !locked;
    el.btnUnlock.disabled = app.busy;
    el.btnPowerCycle.disabled = app.busy || fpga;
    el.btnPowerCycle.title = fpga
      ? "Mode FPGA: cabut daya dilakukan di board, bukan lewat dashboard."
      : "";
    el.btnReset.disabled = app.busy;

    el.voltageControl.hidden = fpga;
    el.autoRow.hidden = fpga;
    el.voltageHint.textContent = fpga
      ? "FPGA membaca tegangan dari ADS1115; slider tidak dipakai."
      : "Putar kenop atau geser nilai";
    el.chartSub.textContent = fpga
      ? "Sampling FPGA ±1 detik · buffer 64 catatan"
      : "1 titik = 3 jam pemakaian · buffer 64 catatan";
    el.actionHint.textContent = fpga
      ? "Riwayat yang tampil adalah dump bertanda tangan dari FPGA. Tekan “Muat riwayat” untuk mengambil sampel terbaru."
      : "Satu sampel mewakili 3 jam pemakaian. Demo memakai satu titik per beberapa detik.";
    el.attackTitle.textContent = fpga ? "BMS curang (host)" : "Simulasi BMS curang";
    el.attackCopy.textContent = fpga
      ? "Dashboard mengubah salinan dump sebelum verifikasi; FPGA tetap memegang kunci."
      : "Ubah data di jalur sebelum stasiun memeriksa.";
    el.footerSource.textContent = fpga
      ? `SeBatt · terhubung ke FPGA via ${data.hardware?.port || "UART"} · clock PL 100 MHz`
      : "SeBatt · chip diemulasikan oleh model protokol Python, belum terhubung ke FPGA";
    el.footerHint.textContent = fpga
      ? "Alur demo: Muat riwayat → Tukar baterai → Hapus/Ubah catatan baru → Tukar baterai."
      : "Alur demo: tukar normal → catat 2,0 V dan hapus → tukar → pulihkan dan ubah angka → tukar.";

    if (locked) {
      el.attackHint.textContent = "Chip terkunci. Buka kunci untuk mengulang skenario demo.";
    } else if (!baseline) {
      el.attackHint.textContent = "Verifikasi riwayat awal dengan “Tukar baterai” sebelum menjalankan serangan.";
    } else if (data.power_cycled && !records.length) {
      el.attackHint.textContent = "Riwayat hilang setelah daya dicabut. Coba “Tukar baterai” untuk melihat ROLLBACK.";
    } else if (!hasNew) {
      el.attackHint.textContent = fpga
        ? "Belum ada catatan baru. Tunggu sampling FPGA, tekan “Muat riwayat”, lalu jalankan serangan."
        : "Belum ada catatan baru. Catat sampel dulu, lalu jalankan serangan.";
    } else {
      el.attackHint.textContent = `${newRecords.length} catatan baru belum diverifikasi. Serang, lalu tekan “Tukar baterai”.`;
    }

    el.autoRecord.checked = app.auto;
    el.autoState.textContent = app.auto ? "aktif" : "nonaktif";
    el.autoState.classList.toggle("on", app.auto);
  }

  function setAuto(enabled) {
    if (isFpga()) enabled = false;
    app.auto = enabled;
    clearInterval(app.autoTimer);
    app.autoTimer = null;
    if (enabled) {
      app.autoTimer = setInterval(() => {
        if (!app.busy && !document.hidden) {
          request("/api/record", { mv: currentMv() });
        }
      }, 2400);
    }
    renderControls();
  }

  async function swap() {
    if (app.busy) return;
    await request("/api/swap");
    if (window.matchMedia("(max-width: 860px)").matches) {
      el.banner.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  async function attack(path) {
    if (app.busy) return;
    const result = await request(path);
    if (result?.message) showToast(result.message);
  }

  async function restore() {
    if (app.busy) return;
    const result = await request("/api/restore");
    if (result) showToast("Catatan dipulihkan. Tekan “Tukar baterai” untuk memeriksa ulang.");
  }

  async function reset() {
    if (app.busy) return;
    setAuto(false);
    const result = await request("/api/reset");
    if (result) {
      showToast(isFpga()
        ? "Tampilan direset. Riwayat FPGA tidak dihapus."
        : "Demo direset ke 16 catatan awal.");
    }
  }

  async function powerCycle() {
    if (app.busy) return;
    setAuto(false);
    const result = await request("/api/power-cycle");
    if (result) showToast("Daya chip dicabut. Coba tukar baterai untuk melihat rollback.");
  }

  async function unlock() {
    if (app.busy) return;
    const result = await request("/api/unlock");
    if (result) showToast("Chip dibuka. Tekan “Tukar baterai” untuk melanjutkan.");
  }

  el.slider.addEventListener("input", updateVoltageLabel);

  document.querySelectorAll("[data-mv]").forEach((button) => {
    button.addEventListener("click", () => {
      setVoltage(Number(button.dataset.mv));
    });
  });

  el.btnSwap.addEventListener("click", swap);
  el.btnRecord.addEventListener("click", () => {
    if (app.busy) return;
    if (isFpga()) request("/api/refresh");
    else request("/api/record", { mv: currentMv() });
  });
  el.btnDelete.addEventListener("click", () => attack("/api/attack/delete"));
  el.btnTamper.addEventListener("click", () => attack("/api/attack/tamper"));
  el.btnRestore.addEventListener("click", restore);
  el.btnReset.addEventListener("click", reset);
  el.btnPowerCycle.addEventListener("click", powerCycle);
  el.btnUnlock.addEventListener("click", unlock);
  el.autoRecord.addEventListener("change", () => setAuto(el.autoRecord.checked));

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (app.data) renderChart(app.data);
    }, 140);
  });

  updateVoltageLabel();
  fetchState();
  setInterval(fetchState, 2000);
})();
