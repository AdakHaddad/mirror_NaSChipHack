// ===========================================================================
//  auth_ctrl.v — UART command engine: auth, history, and locking
//  SeBatt project — Hackathon Deeptech 2026
//
//  Frame: [CMD:1][LEN:2 BE][PAYLOAD:LEN][CRC8:1]  (CRC-8, poly 0x31, MSB first)
//
//  Sampling (spec section 4):
//    auth_ctrl owns the ADS1115 sample loop. Every SAMPLE_CYCLES it starts a
//    conversion (unless the previous one is still busy) and keeps the latest
//    voltage in latest_mv, independently of UART traffic.
//
//    Every completed conversion stores one history record in a 64-entry ring
//    buffer: {seq[31:0], mv[15:0]}. seq starts at 0 at reset and increments
//    per sample. When the buffer is full the oldest record is overwritten and
//    seq keeps counting.
//
//  Record tags (spec sections 4 and 6):
//    Each record is signed once at store time inside the chip:
//      HMAC(K, 0x53 || ID(4) || seq(4) || V(2))  ->  tag per record, tag_mem.
//    READ_HIST costs one summary sign plus the UART transfer; the station can
//    verify every stored tag without re-derivation inside the chip.
//
//  Message prefixes (spec section 6):
//    AUTH     0x41 || nonce(32) || ID(4) || V(2)           = 39 bytes
//    RECORD   0x53 || ID(4) || seq(4) || V(2)              = 11 bytes
//    SUMMARY  0x48 || nonce(32) || ID(4) ||
//             seq_oldest(4) || seq_last(4)                 = 45 bytes
//
//  Commands (spec section 8):
//    0x01 AUTH_REQ nonce(32)   -> 0x02 AUTH_RESP ID(4)|V(2)|tag(32)
//                               or 0x09 CHIP_LOCKED when locked
//    0x07 READ_HIST_REQ nonce(32)
//                               -> 0x08 READ_HIST_RESP
//                                  N(1) || seq_oldest(4) || seq_last(4) ||
//                                  Nx[seq(4)|V(2)|tag(32)] || tag_summary(32)
//                               or 0x09 CHIP_LOCKED when locked
//    0x03 RESULT status(1)     -> no reply; drives the fail counter
//    0x04 LOCK / 0x05 UNLOCK   -> no reply
//    0x06 STATUS               -> 0x06 STATUS_RESP locked(1)|fail_cnt(1)
//                                 (RTL addition; payload not in the spec yet)
//    0x09 CHIP_LOCKED          -> payload = ID(4)
//
//  Locking (spec section 11): any RESULT other than 0x00 VALID and 0x07
//  HISTORY_TRUNCATED bumps the fail counter; three failures in a row lock
//  the chip. UNLOCK or power cycle clears lock and counter.
//
//  Robustness:
//    - The buffer and tag memory are frozen from the READ_HIST snapshot until
//      the last response byte; a sample finishing meanwhile is held and
//      stored afterwards, so a dump never mixes old and new records.
//    - The response CRC is computed from the byte actually transmitted.
//    - The parser drops a partial frame after RX_TIMEOUT_CYCLES of silence,
//      and skips the payload of an oversized frame instead of parsing it.
//    - The switch and ROM sources do not wait for the ADC, so they work with
//      the ADS1115 disconnected.
//
//  Fixed key for the PoC: bytes 0x00..0x1F (matches model/station.py).
// ===========================================================================

module auth_ctrl #(
    parameter integer CLK_HZ = 100_000_000,
    parameter integer BAUD   = 115200,
    parameter [31:0]  BATTERY_ID = 32'h42415401,
    parameter integer SAMPLE_INTERVAL_MS = 1000,
    parameter integer SAMPLE_CYCLES = (CLK_HZ / 1000) * SAMPLE_INTERVAL_MS,
    parameter [15:0]  ROM_MV = 16'd0,       // recorded-set mV until ROM playback exists
    parameter [1:0]   SAMPLE_SOURCE = 2'd0, // 0 ADS1115 (primary), 1 ROM, 2 switch
    parameter integer RX_TIMEOUT_CYCLES = CLK_HZ / 200  // 5 ms idle drops a partial frame
)(
    input  wire        clk,
    input  wire        resetn,

    input  wire        rx,
    output wire        tx,

    output reg         adc_start,
    input  wire [15:0] adc_mv,
    input  wire        adc_valid,
    input  wire        adc_busy,
    input  wire        adc_error,

    input  wire [7:0]  sw,        // board switches: switch source (Basys 3 / Nexys)
    input  wire        src_sel,   // source pin: 0 = SAMPLE_SOURCE, 1 = switch

    output wire        locked_flag,
    output reg  [3:0]  led
);

    // -----------------------------------------------------------------------
    // Voltage source multiplexer (spec section 3)
    // -----------------------------------------------------------------------
    // sw and src_sel are board pins: synchronise them so the value stored in
    // the buffer and the value signed come from the same clean sample.
    reg [1:0] src_sel_sync;
    reg [7:0] sw_s1, sw_s2;

    always @(posedge clk) begin
        src_sel_sync <= {src_sel_sync[0], src_sel};
        sw_s1        <= sw;
        sw_s2        <= sw_s1;
    end

    wire [1:0]  src_sel_code = src_sel_sync[1] ? 2'd2 : SAMPLE_SOURCE;
    wire        src_is_adc   = (src_sel_code == 2'd0);
    wire [15:0] mv_source =
        (src_sel_code == 2'd1) ? ROM_MV :
        (src_sel_code == 2'd2) ? (16'd3000 + sw_s2 * 16'd5) :
                                 adc_mv;

    // -----------------------------------------------------------------------
    // UART
    // -----------------------------------------------------------------------
    wire [7:0] rx_data;
    wire       rx_valid;
    reg  [7:0] tx_byte;
    reg        tx_start;
    wire       tx_busy;
    wire       tx_done;

    uart_if #(
        .CLK_HZ (CLK_HZ),
        .BAUD   (BAUD)
    ) u_uart (
        .clk      (clk),
        .resetn   (resetn),
        .rx       (rx),
        .tx       (tx),
        .rx_data  (rx_data),
        .rx_valid (rx_valid),
        .tx_data  (tx_byte),
        .tx_start (tx_start),
        .tx_busy  (tx_busy),
        .tx_done  (tx_done)
    );

    // -----------------------------------------------------------------------
    // CRC-8, poly 0x31, MSB first
    // -----------------------------------------------------------------------
    function [7:0] crc8_byte;
        input [7:0] crc_in;
        input [7:0] data;
        reg [7:0] c;
        integer k;
        begin
            c = crc_in ^ data;
            for (k = 0; k < 8; k = k + 1)
                c = c[7] ? ((c << 1) ^ 8'h31) : (c << 1);
            crc8_byte = c;
        end
    endfunction

    // -----------------------------------------------------------------------
    // Byte helpers
    // -----------------------------------------------------------------------
    function [7:0] bid_byte;
        input [1:0] idx;
        begin
            case (idx)
                2'd0: bid_byte = BATTERY_ID[31:24];
                2'd1: bid_byte = BATTERY_ID[23:16];
                2'd2: bid_byte = BATTERY_ID[15:8];
                default: bid_byte = BATTERY_ID[7:0];
            endcase
        end
    endfunction

    function [7:0] byte32;
        input [31:0] w;
        input [1:0]  k;
        begin
            case (k)
                2'd0: byte32 = w[31:24];
                2'd1: byte32 = w[23:16];
                2'd2: byte32 = w[15:8];
                default: byte32 = w[7:0];
            endcase
        end
    endfunction

    function [31:0] key_word;
        input [2:0] idx;
        reg [7:0] base;
        begin
            base = {idx, 2'b00};
            key_word = {base, base + 8'd1, base + 8'd2, base + 8'd3};
        end
    endfunction

    // -----------------------------------------------------------------------
    // Command codes (spec section 8)
    // -----------------------------------------------------------------------
    localparam [7:0]
        CMD_AUTH_REQ    = 8'h01,
        CMD_AUTH_RESP   = 8'h02,
        CMD_RESULT      = 8'h03,
        CMD_LOCK        = 8'h04,
        CMD_UNLOCK      = 8'h05,
        CMD_STATUS      = 8'h06,
        CMD_READ_HIST   = 8'h07,
        CMD_HIST_RESP   = 8'h08,
        CMD_CHIP_LOCKED = 8'h09;

    localparam [7:0] ST_VALID     = 8'h00;  // accepted by the station
    localparam [7:0] ST_TRUNCATED = 8'h07;  // accepted with a warning

    localparam [7:0] MSG_AUTH    = 8'h41;
    localparam [7:0] MSG_RECORD  = 8'h53;
    localparam [7:0] MSG_SUMMARY = 8'h48;

    localparam [4:0] MAX_FAILS = 5'd3;

    // -----------------------------------------------------------------------
    // Parser
    // -----------------------------------------------------------------------
    localparam [2:0]
        P_CMD     = 3'd0,
        P_LEN_HI  = 3'd1,
        P_LEN_LO  = 3'd2,
        P_PAYLOAD = 3'd3,
        P_CRC     = 3'd4,
        P_SKIP    = 3'd5;   // discard an oversized frame until the line idles

    reg [2:0]  pstate;
    reg [31:0] rx_idle;
    reg [7:0]  p_cmd;
    reg [15:0] p_len;
    reg [15:0] p_idx;
    reg [7:0]  p_crc;
    reg        frame_valid;
    reg        frame_error;
    reg [7:0]  payload [0:63];

    always @(posedge clk) begin
        if (!resetn) begin
            pstate      <= P_CMD;
            p_cmd       <= 8'd0;
            p_len       <= 16'd0;
            p_idx       <= 16'd0;
            p_crc       <= 8'd0;
            frame_valid <= 1'b0;
            frame_error <= 1'b0;
            rx_idle     <= 32'd0;
        end else begin
            frame_valid <= 1'b0;
            frame_error <= 1'b0;

            // A frame left incomplete by a lost or stray byte is dropped
            // after the line has been idle for RX_TIMEOUT_CYCLES.
            if (rx_valid || pstate == P_CMD)
                rx_idle <= 32'd0;
            else
                rx_idle <= rx_idle + 32'd1;

            if (!rx_valid && pstate != P_CMD &&
                rx_idle >= RX_TIMEOUT_CYCLES - 1) begin
                if (pstate != P_SKIP)
                    frame_error <= 1'b1;
                pstate <= P_CMD;
            end

            if (rx_valid) begin
                case (pstate)
                    P_CMD: begin
                        p_cmd  <= rx_data;
                        p_crc  <= crc8_byte(8'd0, rx_data);
                        pstate <= P_LEN_HI;
                    end

                    P_LEN_HI: begin
                        p_len[15:8] <= rx_data;
                        p_crc       <= crc8_byte(p_crc, rx_data);
                        pstate      <= P_LEN_LO;
                    end

                    P_LEN_LO: begin
                        p_len[7:0] <= rx_data;
                        p_crc      <= crc8_byte(p_crc, rx_data);
                        p_idx      <= 16'd0;
                        if ({p_len[15:8], rx_data} == 16'd0)
                            pstate <= P_CRC;
                        else if ({p_len[15:8], rx_data} > 16'd64) begin
                            frame_error <= 1'b1;
                            pstate      <= P_SKIP;
                        end
                        else
                            pstate <= P_PAYLOAD;
                    end

                    P_PAYLOAD: begin
                        payload[p_idx[5:0]] <= rx_data;
                        p_crc <= crc8_byte(p_crc, rx_data);
                        if ((p_idx + 16'd1) == p_len) begin
                            pstate <= P_CRC;
                        end else begin
                            p_idx <= p_idx + 16'd1;
                        end
                    end

                    P_CRC: begin
                        if (rx_data == p_crc)
                            frame_valid <= 1'b1;
                        else
                            frame_error <= 1'b1;
                        pstate <= P_CMD;
                    end

                    P_SKIP: ;

                    default: pstate <= P_CMD;
                endcase
            end
        end
    end

    // -----------------------------------------------------------------------
    // State and storage declarations
    // -----------------------------------------------------------------------
    localparam [3:0]
        M_IDLE      = 4'd0,
        M_WAIT      = 4'd1,   // wait for the latest sample + free AXI master
        M_WR        = 4'd2,
        M_WR_WAIT   = 4'd3,
        M_POLL      = 4'd4,
        M_POLL_WAIT = 4'd5,
        M_RD        = 4'd6,
        M_RD_WAIT   = 4'd7,
        M_TX        = 4'd8,
        M_TX_WAIT   = 4'd9;

    localparam [3:0]
        SG_IDLE      = 4'd0,
        SG_BUILD     = 4'd1,
        SG_WR        = 4'd2,
        SG_WR_WAIT   = 4'd3,
        SG_POLL      = 4'd4,
        SG_POLL_WAIT = 4'd5,
        SG_RD        = 4'd6,
        SG_RD_WAIT   = 4'd7;

    reg [3:0]  mstate;
    reg [7:0]  pend_cmd;      // command in service: CMD_AUTH_REQ / CMD_READ_HIST
    reg [4:0]  wr_idx;
    reg [4:0]  wr_last;       // index of the CTRL/start write
    reg [2:0]  rd_idx;
    reg [11:0] tx_idx;
    reg [11:0] tx_total;      // frame length including CRC
    reg [7:0]  tx_crc;

    reg [7:0]  resp_cmd;
    reg [11:0] resp_plen;     // response payload length

    reg [7:0]  hash_bytes [0:31];    // main engine HMAC result
    reg [7:0]  summary_tag [0:31];   // summary tag for READ_HIST_RESP
    reg [7:0]  msg_bytes  [0:63];    // HMAC message buffer
    reg [6:0]  msg_len;
    reg [3:0]  msg_words;
    reg [7:0]  nonce_mem  [0:31];
    reg [15:0] voltage;

    reg        auth_ok;
    reg        auth_error;
    reg        locked_r;
    reg [4:0]  fail_cnt;

    // History storage: ring buffer of {seq[31:0], mv[15:0]}
    reg [47:0] buf_mem [0:63];
    reg [31:0] seq_next;      // sequence number assigned to the next sample
    reg [5:0]  buf_wr;
    reg [6:0]  buf_cnt;       // saturates at 64

    // Per-record tags: 64 records x 8 words
    reg [31:0] tag_mem [0:511];

    // Sampling loop
    reg [31:0] sample_cnt;
    reg        sample_busy;
    reg [15:0] latest_mv;
    reg        latest_valid;
    reg        latest_error;

    // READ_HIST_RESP snapshot
    reg [6:0]  hist_n;
    reg [31:0] hist_oldest;
    reg [31:0] hist_last;
    reg [5:0]  hist_base;
    wire [31:0] hist_oldest_next = seq_next - {25'd0, buf_cnt};
    wire [31:0] hist_last_next   = seq_next - 32'd1;

    // Record signer request: the newest record wins when a tag is still
    // running. At the production ratio (sign ~5 us per 1 s sample) the
    // queue never overlaps; a dump holds new samples (see commit_now).
    reg        sg_req;
    reg [31:0] sg_req_seq;
    reg [15:0] sg_req_mv;
    reg [5:0]  sg_req_phys;

    reg [3:0]  sg_state;
    reg [4:0]  sg_wr_idx;
    reg [2:0]  sg_rd_idx;
    reg [31:0] sg_seq;
    reg [15:0] sg_mv;
    reg [5:0]  sg_phys;
    reg        sg_busy;
    reg        cmd_reserve;

    // Sample commit. A sample is done when the ADC answers or, for the
    // switch/ROM sources, at the interval tick without touching the ADC.
    // While a READ_HIST is between snapshot and last byte the buffer and tag
    // memory stay frozen; a finished sample waits in hold_* (one slot, so in
    // 100 ms mode a second sample during a dump replaces the first).
    reg        hold_valid;
    reg [15:0] hold_mv;

    wire sample_tick = (sample_cnt >= SAMPLE_CYCLES - 1);
    wire direct_tick = sample_tick && !src_is_adc && !sample_busy;
    wire sample_done = (sample_busy && adc_valid) || direct_tick;
    wire dump_active = (pend_cmd == CMD_READ_HIST) && (mstate != M_IDLE);
    wire commit_now  = !dump_active && (hold_valid || sample_done);
    wire [15:0] commit_mv = hold_valid ? hold_mv : mv_source;

    // Sign engine AXI drives; the signer wins the mux while busy, and the
    // command FSM only starts a sign from M_WAIT once the signer is done.
    reg        sg_axi_start;
    reg        sg_axi_wr;
    reg  [7:0] sg_axi_addr;
    reg  [31:0] sg_axi_wdata;

    reg        mm_axi_start;
    reg        mm_axi_wr;
    reg  [7:0] mm_axi_addr;
    reg  [31:0] mm_axi_wdata;

    wire        axi_start = sg_busy ? sg_axi_start : mm_axi_start;
    wire        axi_wr    = sg_busy ? sg_axi_wr    : mm_axi_wr;
    wire [7:0]  axi_addr  = sg_busy ? sg_axi_addr  : mm_axi_addr;
    wire [31:0] axi_wdata = sg_busy ? sg_axi_wdata : mm_axi_wdata;

    wire [31:0] axi_rd_data;
    wire        axi_busy;
    wire        axi_done;
    wire        axi_err;

    wire [7:0]  axi_awaddr;
    wire        axi_awvalid;
    wire        axi_awready;
    wire [31:0] axi_wdata_bus;
    wire [3:0]  axi_wstrb;
    wire        axi_wvalid;
    wire        axi_wready;
    wire [1:0]  axi_bresp;
    wire        axi_bvalid;
    wire        axi_bready;
    wire [7:0]  axi_araddr;
    wire        axi_arvalid;
    wire        axi_arready;
    wire [31:0] axi_rdata_bus;
    wire [1:0]  axi_rresp;
    wire        axi_rvalid;
    wire        axi_rready;

    axil_master #(
        .ADDR_WIDTH (8),
        .DATA_WIDTH (32)
    ) u_axil (
        .clk            (clk),
        .resetn         (resetn),
        .start          (axi_start),
        .wr             (axi_wr),
        .addr           (axi_addr),
        .wdata          (axi_wdata),
        .rdata          (axi_rd_data),
        .busy           (axi_busy),
        .done           (axi_done),
        .error          (axi_err),

        .m_axil_awaddr  (axi_awaddr),
        .m_axil_awvalid (axi_awvalid),
        .m_axil_awready (axi_awready),
        .m_axil_wdata   (axi_wdata_bus),
        .m_axil_wstrb   (axi_wstrb),
        .m_axil_wvalid  (axi_wvalid),
        .m_axil_wready  (axi_wready),
        .m_axil_bresp   (axi_bresp),
        .m_axil_bvalid  (axi_bvalid),
        .m_axil_bready  (axi_bready),
        .m_axil_araddr  (axi_araddr),
        .m_axil_arvalid (axi_arvalid),
        .m_axil_arready (axi_arready),
        .m_axil_rdata   (axi_rdata_bus),
        .m_axil_rresp   (axi_rresp),
        .m_axil_rvalid  (axi_rvalid),
        .m_axil_rready  (axi_rready)
    );

    hmac_sha256 u_hmac (
        .s_axi_aclk    (clk),
        .s_axi_aresetn (resetn),
        .s_axi_awaddr  (axi_awaddr),
        .s_axi_awprot  (3'b000),
        .s_axi_awvalid (axi_awvalid),
        .s_axi_awready (axi_awready),
        .s_axi_wdata   (axi_wdata_bus),
        .s_axi_wstrb   (axi_wstrb),
        .s_axi_wvalid  (axi_wvalid),
        .s_axi_wready  (axi_wready),
        .s_axi_bresp   (axi_bresp),
        .s_axi_bvalid  (axi_bvalid),
        .s_axi_bready  (axi_bready),
        .s_axi_araddr  (axi_araddr),
        .s_axi_arprot  (3'b000),
        .s_axi_arvalid (axi_arvalid),
        .s_axi_arready (axi_arready),
        .s_axi_rdata   (axi_rdata_bus),
        .s_axi_rresp   (axi_rresp),
        .s_axi_rvalid  (axi_rvalid),
        .s_axi_rready  (axi_rready)
    );

    function [31:0] msg_word;
        input [3:0] idx;
        begin
            msg_word = {msg_bytes[idx*4], msg_bytes[idx*4+1],
                        msg_bytes[idx*4+2], msg_bytes[idx*4+3]};
        end
    endfunction

    // The signer may run while the command FSM is idle, waiting for a
    // sample, or transmitting. cmd_reserve closes the one-cycle race where a
    // sample request and a command both try to leave M_WAIT together.
    wire cmd_bus_free = (mstate == M_IDLE) || (mstate == M_WAIT) ||
                        (mstate == M_TX)   || (mstate == M_TX_WAIT);

    // -----------------------------------------------------------------------
    // Response payload byte selection
    // -----------------------------------------------------------------------
    function [7:0] hist_payload_byte;
        input [11:0] idx;
        reg [11:0] off;
        reg [11:0] in_rec;
        reg [6:0]  jval;
        reg [5:0]  phys;
        reg [47:0] rec;
        reg [31:0] wval;
        reg [8:0]  tm;
        reg [4:0]  tb;
        begin
            if (idx == 12'd0) begin
                hist_payload_byte = {1'b0, hist_n[6:0]};
            end else if (idx <= 12'd4) begin
                hist_payload_byte = byte32(hist_oldest, idx[1:0] - 2'd1);
            end else if (idx <= 12'd8) begin
                hist_payload_byte = byte32(hist_last, idx[1:0] - 2'd1);
            end else begin
                off = idx - 12'd9;
                if (off < ({4'd0, hist_n} * 12'd38)) begin
                    jval   = off / 12'd38;
                    in_rec = off - (jval * 12'd38);
                    phys   = hist_base + jval[5:0];
                    rec    = buf_mem[phys];
                    if (in_rec < 12'd4) begin
                        hist_payload_byte = byte32(rec[47:16], in_rec[1:0]);
                    end else if (in_rec == 12'd4) begin
                        hist_payload_byte = rec[15:8];
                    end else if (in_rec == 12'd5) begin
                        hist_payload_byte = rec[7:0];
                    end else begin
                        tb = in_rec - 12'd6;        // 0..31 tag byte position
                        tm = {phys, tb[4:2]};       // tag word: phys*8 + tb/4
                        wval = tag_mem[tm];
                        hist_payload_byte = byte32(wval, tb[1:0]);
                    end
                end else begin
                    hist_payload_byte = summary_tag[off - {4'd0, hist_n} * 12'd38];
                end
            end
        end
    endfunction

    function [7:0] resp_payload_byte;
        input [11:0] idx;
        begin
            case (resp_cmd)
                CMD_AUTH_RESP: begin
                    if (idx < 6'd4) begin
                        resp_payload_byte = bid_byte(idx[1:0]);
                    end else if (idx == 6'd4) begin
                        resp_payload_byte = voltage[15:8];
                    end else if (idx == 6'd5) begin
                        resp_payload_byte = voltage[7:0];
                    end else begin
                        resp_payload_byte = hash_bytes[idx - 6'd6];
                    end
                end

                CMD_CHIP_LOCKED: begin
                    resp_payload_byte = bid_byte(idx[1:0]);
                end

                CMD_STATUS: begin
                    if (idx == 12'd0)
                        resp_payload_byte = {7'd0, locked_r};
                    else
                        resp_payload_byte = {3'd0, fail_cnt};
                end

                default: resp_payload_byte = hist_payload_byte(idx);
            endcase
        end
    endfunction

    function [7:0] frame_byte;
        input [11:0] idx;
        begin
            case (idx)
                12'd0: frame_byte = resp_cmd;
                12'd1: frame_byte = resp_plen[11:8];
                12'd2: frame_byte = resp_plen[7:0];
                default: frame_byte = resp_payload_byte(idx - 12'd3);
            endcase
        end
    endfunction

    // -----------------------------------------------------------------------
    // Command FSM and record signer: both engines share one always block so
    // the message buffer and the AXI master have exactly one driver set.
    // -----------------------------------------------------------------------
    integer j;

    always @(posedge clk) begin
        if (!resetn) begin
            mstate       <= M_IDLE;
            pend_cmd     <= 8'd0;
            wr_idx       <= 5'd0;
            wr_last      <= 5'd0;
            rd_idx       <= 3'd0;
            tx_idx       <= 12'd0;
            tx_total     <= 12'd0;
            tx_crc       <= 8'd0;
            resp_cmd     <= 8'd0;
            resp_plen    <= 12'd0;
            voltage      <= 16'd0;
            auth_ok      <= 1'b0;
            auth_error   <= 1'b0;
            locked_r     <= 1'b0;
            fail_cnt     <= 5'd0;
            hist_n       <= 7'd0;
            hist_oldest  <= 32'd0;
            hist_last    <= 32'd0;
            hist_base    <= 6'd0;
            sg_req       <= 1'b0;
            sg_busy      <= 1'b0;
            cmd_reserve  <= 1'b0;
            sg_req_seq   <= 32'd0;
            sg_req_mv    <= 16'd0;
            sg_req_phys  <= 6'd0;
            sg_state     <= SG_IDLE;
            sg_wr_idx    <= 5'd0;
            sg_rd_idx    <= 3'd0;
            sg_seq       <= 32'd0;
            sg_mv        <= 16'd0;
            sg_phys      <= 6'd0;
            sg_axi_start <= 1'b0;
            sg_axi_wr    <= 1'b0;
            sg_axi_addr  <= 8'd0;
            sg_axi_wdata <= 32'd0;
            mm_axi_start <= 1'b0;
            mm_axi_wr    <= 1'b0;
            mm_axi_addr  <= 8'd0;
            mm_axi_wdata <= 32'd0;
            tx_start     <= 1'b0;
            msg_len      <= 7'd0;
            msg_words    <= 4'd0;
            for (j = 0; j < 64; j = j + 1)  msg_bytes[j]   <= 8'd0;
            for (j = 0; j < 32; j = j + 1)  hash_bytes[j]  <= 8'd0;
            for (j = 0; j < 32; j = j + 1)  summary_tag[j] <= 8'd0;
            for (j = 0; j < 32; j = j + 1)  nonce_mem[j]   <= 8'd0;
        end else begin
            // -------------------------------------------------------------
            // Record signer: store-time signing of one record tag
            // -------------------------------------------------------------
            sg_axi_start <= 1'b0;

            // Claim the signer (and the bus) when free; cmd_reserve is set
            // by M_WAIT before the command FSM owns the bus.
            if (sg_req && !sg_busy && cmd_bus_free && !cmd_reserve) begin
                sg_req    <= 1'b0;
                sg_seq    <= sg_req_seq;
                sg_mv     <= sg_req_mv;
                sg_phys   <= sg_req_phys;
                sg_busy   <= 1'b1;
                sg_state  <= SG_BUILD;
                sg_wr_idx <= 5'd0;
            end

            // A committed sample becomes a pending signer request. It comes
            // after the claim above so a request landing on the claim edge
            // is kept rather than cleared. It lives in the same always block
            // as the signer so sg_req* have exactly one driver.
            if (commit_now) begin
                sg_req      <= 1'b1;
                sg_req_seq  <= seq_next;
                sg_req_mv   <= commit_mv;
                sg_req_phys <= buf_wr;
            end

            case (sg_state)
                SG_IDLE: ;

                SG_BUILD: begin
                    // msg = 0x53 || ID(4) || seq(4) || V(2), zero padded
                    msg_bytes[0]  <= MSG_RECORD;
                    msg_bytes[1]  <= bid_byte(2'd0);
                    msg_bytes[2]  <= bid_byte(2'd1);
                    msg_bytes[3]  <= bid_byte(2'd2);
                    msg_bytes[4]  <= bid_byte(2'd3);
                    msg_bytes[5]  <= sg_seq[31:24];
                    msg_bytes[6]  <= sg_seq[23:16];
                    msg_bytes[7]  <= sg_seq[15:8];
                    msg_bytes[8]  <= sg_seq[7:0];
                    msg_bytes[9]  <= sg_mv[15:8];
                    msg_bytes[10] <= sg_mv[7:0];
                    msg_bytes[11] <= 8'h00;
                    sg_state <= SG_WR;
                end

                SG_WR: begin
                    if (!axi_busy) begin
                        sg_axi_wr <= 1'b1;
                        if (sg_wr_idx < 5'd8) begin
                            sg_axi_addr  <= 8'h10 + {sg_wr_idx[2:0], 2'b00};
                            sg_axi_wdata <= key_word(sg_wr_idx[2:0]);
                        end else if (sg_wr_idx < 5'd11) begin
                            sg_axi_addr  <= 8'h30 + {(sg_wr_idx - 5'd8), 2'b00};
                            sg_axi_wdata <= msg_word(sg_wr_idx[3:0] - 4'd8);
                        end else if (sg_wr_idx == 5'd11) begin
                            sg_axi_addr  <= 8'h08;
                            sg_axi_wdata <= 32'd11;   // message length
                        end else begin
                            sg_axi_addr  <= 8'h00;
                            sg_axi_wdata <= 32'd1;    // CTRL start
                        end
                        sg_axi_start <= 1'b1;
                        sg_state     <= SG_WR_WAIT;
                    end
                end

                SG_WR_WAIT: begin
                    if (axi_done) begin
                        if (sg_wr_idx == 5'd12) begin
                            sg_state <= SG_POLL;
                        end else begin
                            sg_wr_idx <= sg_wr_idx + 5'd1;
                            sg_state  <= SG_WR;
                        end
                    end
                end

                SG_POLL: begin
                    if (!axi_busy) begin
                        sg_axi_wr    <= 1'b0;
                        sg_axi_addr  <= 8'h04;
                        sg_axi_start <= 1'b1;
                        sg_state     <= SG_POLL_WAIT;
                    end
                end

                SG_POLL_WAIT: begin
                    if (axi_done) begin
                        if (axi_rd_data[0]) begin
                            sg_rd_idx <= 3'd0;
                            sg_state  <= SG_RD;
                        end else begin
                            sg_state <= SG_POLL;
                        end
                    end
                end

                SG_RD: begin
                    if (!axi_busy) begin
                        sg_axi_wr    <= 1'b0;
                        sg_axi_addr  <= 8'h70 + {sg_rd_idx, 2'b00};
                        sg_axi_start <= 1'b1;
                        sg_state     <= SG_RD_WAIT;
                    end
                end

                SG_RD_WAIT: begin
                    if (axi_done) begin
                        tag_mem[{sg_phys, sg_rd_idx}] <= axi_rd_data;
                        if (sg_rd_idx == 3'd7) begin
                            sg_busy  <= 1'b0;
                            sg_state <= SG_IDLE;
                        end else begin
                            sg_rd_idx <= sg_rd_idx + 3'd1;
                            sg_state  <= SG_RD;
                        end
                    end
                end

                default: begin
                    sg_busy  <= 1'b0;
                    sg_state <= SG_IDLE;
                end
            endcase

            // -------------------------------------------------------------
            // Command FSM
            // -------------------------------------------------------------
            mm_axi_start <= 1'b0;
            tx_start     <= 1'b0;

            if (axi_err) begin
                auth_error <= 1'b1;
                auth_ok    <= 1'b0;
            end

            if (frame_error) begin
                auth_error <= 1'b1;
                auth_ok    <= 1'b0;
            end

            // A frame arriving mid-operation is dropped: the station sends
            // one frame at a time (spec section 10).
            if (frame_valid && mstate != M_IDLE) begin
                auth_error <= 1'b1;
                auth_ok    <= 1'b0;
            end

            case (mstate)
                M_IDLE: begin
                    if (frame_valid) begin
                        case (p_cmd)
                            CMD_AUTH_REQ: begin
                                if (p_len == 16'd32) begin
                                    for (j = 0; j < 32; j = j + 1)
                                        nonce_mem[j] <= payload[j];
                                    if (locked_r) begin
                                        pend_cmd  <= 8'd0;
                                        resp_cmd  <= CMD_CHIP_LOCKED;
                                        resp_plen <= 12'd4;
                                        tx_idx    <= 12'd0;
                                        tx_total  <= 12'd8;
                                        tx_crc    <= 8'd0;
                                        mstate    <= M_TX;
                                    end else begin
                                        pend_cmd <= CMD_AUTH_REQ;
                                        mstate   <= M_WAIT;
                                    end
                                end else begin
                                    auth_error <= 1'b1;
                                end
                            end

                            CMD_READ_HIST: begin
                                if (p_len == 16'd32) begin
                                    for (j = 0; j < 32; j = j + 1)
                                        nonce_mem[j] <= payload[j];
                                    if (locked_r) begin
                                        pend_cmd  <= 8'd0;
                                        resp_cmd  <= CMD_CHIP_LOCKED;
                                        resp_plen <= 12'd4;
                                        tx_idx    <= 12'd0;
                                        tx_total  <= 12'd8;
                                        tx_crc    <= 8'd0;
                                        mstate    <= M_TX;
                                    end else begin
                                        pend_cmd <= CMD_READ_HIST;
                                        mstate   <= M_WAIT;
                                    end
                                end else begin
                                    auth_error <= 1'b1;
                                end
                            end

                            // RESULT VALID / HISTORY_TRUNCATED reset the fail
                            // counter; every other status bumps it and locks
                            // the chip on the third failure (spec section 11).
                            // The green/red LEDs show this last verdict.
                            CMD_RESULT: begin
                                if (p_len == 16'd1) begin
                                    if (payload[0] == ST_VALID ||
                                        payload[0] == ST_TRUNCATED) begin
                                        fail_cnt   <= 5'd0;
                                        auth_ok    <= 1'b1;
                                        auth_error <= 1'b0;
                                    end else begin
                                        if (fail_cnt < MAX_FAILS)
                                            fail_cnt <= fail_cnt + 5'd1;
                                        if (fail_cnt == MAX_FAILS - 5'd1)
                                            locked_r <= 1'b1;
                                        auth_ok    <= 1'b0;
                                        auth_error <= 1'b1;
                                    end
                                end else begin
                                    auth_error <= 1'b1;
                                end
                            end

                            CMD_LOCK: begin
                                if (p_len == 16'd0) begin
                                    locked_r <= 1'b1;
                                    auth_ok  <= 1'b0;
                                end else begin
                                    auth_error <= 1'b1;
                                end
                            end

                            CMD_UNLOCK: begin
                                if (p_len == 16'd0) begin
                                    locked_r   <= 1'b0;
                                    fail_cnt   <= 5'd0;
                                    auth_error <= 1'b0;
                                end else begin
                                    auth_error <= 1'b1;
                                end
                            end

                            CMD_STATUS: begin
                                if (p_len == 16'd0) begin
                                    pend_cmd  <= 8'd0;
                                    resp_cmd  <= CMD_STATUS;
                                    resp_plen <= 12'd2;
                                    tx_idx    <= 12'd0;
                                    tx_total  <= 12'd6;
                                    tx_crc    <= 8'd0;
                                    mstate    <= M_TX;
                                end else begin
                                    auth_error <= 1'b1;
                                end
                            end

                            default: auth_error <= 1'b1;
                        endcase
                    end
                end

                // A signed command proceeds once the latest sample exists,
                // every queued record tag is done, and the AXI master is
                // free; the wait stays well inside the 2 s station timeout.
                M_WAIT: begin
                    if (latest_valid && !sg_busy && !sg_req) begin
                        cmd_reserve <= 1'b1;
                        for (j = 0; j < 64; j = j + 1)
                            msg_bytes[j] <= 8'd0;
                        msg_bytes[33] <= bid_byte(2'd0);
                        msg_bytes[34] <= bid_byte(2'd1);
                        msg_bytes[35] <= bid_byte(2'd2);
                        msg_bytes[36] <= bid_byte(2'd3);
                        if (pend_cmd == CMD_AUTH_REQ) begin
                            msg_bytes[0] <= MSG_AUTH;
                            for (j = 1; j <= 32; j = j + 1)
                                msg_bytes[j] <= nonce_mem[j - 1];
                            msg_bytes[37] <= latest_mv[15:8];
                            msg_bytes[38] <= latest_mv[7:0];
                            voltage   <= latest_mv;
                            resp_cmd  <= CMD_AUTH_RESP;
                            resp_plen <= 12'd38;
                            tx_total  <= 12'd42;
                            msg_len   <= 7'd39;
                            msg_words <= 4'd10;
                            wr_last   <= 5'd19;   // 8 key + 10 msg + LEN + start
                        end else begin
                            // READ_HIST: snapshot the buffer, then sign the
                            // summary binding the nonce to the true range.
                            hist_n      <= buf_cnt;
                            hist_oldest <= hist_oldest_next;
                            hist_last   <= hist_last_next;
                            hist_base   <= (buf_wr - buf_cnt[5:0]);
                            resp_cmd    <= CMD_HIST_RESP;
                            resp_plen   <= 12'd41 + {5'd0, buf_cnt} * 12'd38;
                            tx_total    <= 12'd45 + {5'd0, buf_cnt} * 12'd38;
                            msg_bytes[0] <= MSG_SUMMARY;
                            for (j = 1; j <= 32; j = j + 1)
                                msg_bytes[j] <= nonce_mem[j - 1];
                            msg_bytes[37] <= hist_oldest_next[31:24];
                            msg_bytes[38] <= hist_oldest_next[23:16];
                            msg_bytes[39] <= hist_oldest_next[15:8];
                            msg_bytes[40] <= hist_oldest_next[7:0];
                            msg_bytes[41] <= hist_last_next[31:24];
                            msg_bytes[42] <= hist_last_next[23:16];
                            msg_bytes[43] <= hist_last_next[15:8];
                            msg_bytes[44] <= hist_last_next[7:0];
                            msg_len   <= 7'd45;
                            msg_words <= 4'd12;
                            wr_last   <= 5'd21;   // 8 key + 12 msg + LEN + start
                        end
                        wr_idx <= 5'd0;
                        rd_idx <= 3'd0;
                        mstate <= M_WR;
                    end
                end

                M_WR: begin
                    if (!axi_busy) begin
                        mm_axi_wr <= 1'b1;
                        if (wr_idx < 5'd8) begin
                            mm_axi_addr  <= 8'h10 + {wr_idx[2:0], 2'b00};
                            mm_axi_wdata <= key_word(wr_idx[2:0]);
                        end else if (wr_idx < 5'd8 + {1'b0, msg_words}) begin
                            mm_axi_addr  <= 8'h30 + {(wr_idx - 5'd8), 2'b00};
                            mm_axi_wdata <= msg_word(wr_idx[3:0] - 4'd8);
                        end else if (wr_idx == 5'd8 + {1'b0, msg_words}) begin
                            mm_axi_addr  <= 8'h08;
                            mm_axi_wdata <= {24'd0, msg_len};
                        end else begin
                            mm_axi_addr  <= 8'h00;
                            mm_axi_wdata <= 32'd1;
                        end
                        mm_axi_start <= 1'b1;
                        mstate       <= M_WR_WAIT;
                    end
                end

                M_WR_WAIT: begin
                    if (axi_done) begin
                        if (wr_idx == wr_last) begin
                            mstate <= M_POLL;
                        end else begin
                            wr_idx <= wr_idx + 5'd1;
                            mstate <= M_WR;
                        end
                    end
                end

                M_POLL: begin
                    if (!axi_busy) begin
                        mm_axi_wr    <= 1'b0;
                        mm_axi_addr  <= 8'h04;
                        mm_axi_start <= 1'b1;
                        mstate       <= M_POLL_WAIT;
                    end
                end

                M_POLL_WAIT: begin
                    if (axi_done) begin
                        if (axi_rd_data[0]) begin
                            rd_idx <= 3'd0;
                            mstate <= M_RD;
                        end else begin
                            mstate <= M_POLL;
                        end
                    end
                end

                M_RD: begin
                    if (!axi_busy) begin
                        mm_axi_wr    <= 1'b0;
                        mm_axi_addr  <= 8'h70 + {rd_idx, 2'b00};
                        mm_axi_start <= 1'b1;
                        mstate       <= M_RD_WAIT;
                    end
                end

                M_RD_WAIT: begin
                    if (axi_done) begin
                        hash_bytes[{rd_idx, 2'b00}]        <= axi_rd_data[31:24];
                        hash_bytes[{rd_idx, 2'b00} + 6'd1] <= axi_rd_data[23:16];
                        hash_bytes[{rd_idx, 2'b00} + 6'd2] <= axi_rd_data[15:8];
                        hash_bytes[{rd_idx, 2'b00} + 6'd3] <= axi_rd_data[7:0];
                        if (pend_cmd == CMD_READ_HIST) begin
                            summary_tag[{rd_idx, 2'b00}]        <= axi_rd_data[31:24];
                            summary_tag[{rd_idx, 2'b00} + 6'd1] <= axi_rd_data[23:16];
                            summary_tag[{rd_idx, 2'b00} + 6'd2] <= axi_rd_data[15:8];
                            summary_tag[{rd_idx, 2'b00} + 6'd3] <= axi_rd_data[7:0];
                        end
                        if (rd_idx == 3'd7) begin
                            tx_idx <= 12'd0;
                            tx_crc <= 8'd0;
                            mstate <= M_TX;
                        end else begin
                            rd_idx <= rd_idx + 3'd1;
                            mstate <= M_RD;
                        end
                    end
                end

                M_TX: begin
                    cmd_reserve <= 1'b0;
                    if (tx_idx < tx_total) begin
                        if (tx_idx == tx_total - 12'd1)
                            tx_byte <= tx_crc;
                        else
                            tx_byte <= frame_byte(tx_idx);
                        tx_start <= 1'b1;
                        mstate   <= M_TX_WAIT;
                    end else begin
                        mstate  <= M_IDLE;
                    end
                end

                M_TX_WAIT: begin
                    if (tx_done) begin
                        // CRC over the byte that went out on the wire, not a
                        // second read of the response memory.
                        if (tx_idx < tx_total - 12'd1)
                            tx_crc <= crc8_byte(tx_crc, tx_byte);
                        tx_idx <= tx_idx + 12'd1;
                        mstate <= M_TX;
                    end
                end

                default: mstate <= M_IDLE;
            endcase
        end
    end

    // -----------------------------------------------------------------------
    // Sampling loop, ring buffer, and per-record tag requests
    // -----------------------------------------------------------------------
    always @(posedge clk) begin
        if (!resetn) begin
            adc_start    <= 1'b0;
            sample_cnt   <= 32'd0;
            sample_busy  <= 1'b0;
            latest_mv    <= 16'd0;
            latest_valid <= 1'b0;
            latest_error <= 1'b0;
            seq_next     <= 32'd0;
            buf_wr       <= 6'd0;
            buf_cnt      <= 7'd0;
            hold_valid   <= 1'b0;
            hold_mv      <= 16'd0;
        end else begin
            adc_start <= 1'b0;

            // Periodic loop: conversions are spaced SAMPLE_CYCLES apart,
            // start to start when the ADC is faster than the interval. The
            // request waits if a conversion is still in flight, so an
            // interval can stretch but never collapse. The switch and ROM
            // sources complete at the tick itself (direct_tick).
            if (sample_tick) begin
                if (!src_is_adc) begin
                    if (!sample_busy)
                        sample_cnt <= 32'd0;
                end else if (!sample_busy && !adc_busy) begin
                    adc_start   <= 1'b1;
                    sample_busy <= 1'b1;
                    sample_cnt  <= 32'd0;
                end
            end else begin
                sample_cnt <= sample_cnt + 32'd1;
            end

            if (sample_done) begin
                latest_mv    <= mv_source;
                latest_valid <= 1'b1;
                latest_error <= 1'b0;
                if (sample_busy)
                    sample_busy <= 1'b0;
            end

            // Store the record (held sample first); the command/signer block
            // requests its tag on the same edge from commit_now/commit_mv.
            if (commit_now) begin
                buf_mem[buf_wr] <= {seq_next, commit_mv};
                seq_next        <= seq_next + 32'd1;
                buf_wr          <= buf_wr + 6'd1;
                if (buf_cnt < 7'd64)
                    buf_cnt <= buf_cnt + 7'd1;
            end

            // Hold slot: filled while a dump is in progress, drained by the
            // commit above once it ends. A sample finishing on the drain
            // edge takes the slot for the next cycle.
            if (sample_done && (dump_active || hold_valid)) begin
                hold_valid <= 1'b1;
                hold_mv    <= mv_source;
            end else if (commit_now) begin
                hold_valid <= 1'b0;
            end

            // ads1115_ctrl keeps error high until it sees the next start, so
            // ignore it during the start pulse itself.
            if (sample_busy && !adc_valid) begin
                if (adc_error && !adc_start) begin
                    // Keep the last good sample if there is one; otherwise
                    // expose 0 mV so a request still completes. No record is
                    // stored for a failed read.
                    if (!latest_valid) begin
                        latest_mv    <= 16'd0;
                        latest_valid <= 1'b1;
                    end
                    latest_error <= 1'b1;
                    sample_busy  <= 1'b0;
                end
            end
        end
    end

    // -----------------------------------------------------------------------
    // LEDs: heartbeat, busy, last station verdict accepted (green), and
    // locked / last verdict rejected / protocol or ADC error (red). A RESULT
    // VALID or UNLOCK clears the error; the ADC error clears on a good read.
    // -----------------------------------------------------------------------
    reg [23:0] hb_cnt;

    always @(posedge clk) begin
        if (!resetn) begin
            hb_cnt <= 24'd0;
            led    <= 4'd0;
        end else begin
            hb_cnt <= hb_cnt + 24'd1;
            led[0] <= hb_cnt[23];
            led[1] <= (mstate != M_IDLE) || sg_busy || axi_busy || tx_busy;
            led[2] <= auth_ok;
            led[3] <= locked_r || auth_error || latest_error;
        end
    end

    assign locked_flag = locked_r;

endmodule
