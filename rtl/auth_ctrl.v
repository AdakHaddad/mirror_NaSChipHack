// ===========================================================================
//  auth_ctrl.v — UART frame parser + challenge-response engine
//  SeBatt project — Hackathon Deeptech 2026
//
//  Frame: [CMD:1][LEN:2 BE][PAYLOAD:LEN][CRC8:1]  (CRC-8/MAXIM, poly 0x31)
//
//  AUTH_REQ (0x01, 32-byte nonce):
//    1. Start one ADS1115 conversion and wait for adc_valid.
//    2. Build msg = nonce || battery_id(4) || voltage(2 BE).
//    3. Write key + msg to hmac_sha256 over AXI4-Lite, start, poll done.
//    4. Read the 32-byte HMAC.
//    5. Send AUTH_RESP (0x02): battery_id(4) || voltage(2) || hmac(32).
//
//  Fixed key for the PoC: bytes 0x00..0x1F (matches model/station.py).
// ===========================================================================

module auth_ctrl #(
    parameter integer CLK_HZ = 100_000_000,
    parameter integer BAUD   = 115200,
    parameter [31:0]  BATTERY_ID = 32'h42415401
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

    output reg  [3:0]  led
);

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
    // CRC-8/MAXIM
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
    // Fixed identity helpers
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

    function [31:0] key_word;
        input [2:0] idx;
        reg [7:0] base;
        begin
            base = {idx, 2'b00};
            key_word = {base, base + 8'd1, base + 8'd2, base + 8'd3};
        end
    endfunction

    // -----------------------------------------------------------------------
    // Parser
    // -----------------------------------------------------------------------
    localparam [2:0]
        P_CMD    = 3'd0,
        P_LEN_HI = 3'd1,
        P_LEN_LO = 3'd2,
        P_PAYLOAD= 3'd3,
        P_CRC    = 3'd4;

    reg [2:0]  pstate;
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
        end else begin
            frame_valid <= 1'b0;
            frame_error <= 1'b0;

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
                            pstate      <= P_CMD;
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

                    default: pstate <= P_CMD;
                endcase
            end
        end
    end

    // -----------------------------------------------------------------------
    // Message / response storage
    // -----------------------------------------------------------------------
    reg [7:0] msg_bytes  [0:63];
    reg [7:0] hash_bytes [0:31];
    reg [15:0] voltage;

    function [31:0] msg_word;
        input [3:0] idx;
        begin
            msg_word = {msg_bytes[idx*4], msg_bytes[idx*4+1],
                        msg_bytes[idx*4+2], msg_bytes[idx*4+3]};
        end
    endfunction

    function [7:0] resp_byte;
        input [5:0] idx;
        begin
            if (idx < 6'd4)
                resp_byte = bid_byte(idx[1:0]);
            else if (idx == 6'd4)
                resp_byte = voltage[15:8];
            else if (idx == 6'd5)
                resp_byte = voltage[7:0];
            else
                resp_byte = hash_bytes[idx - 6'd6];
        end
    endfunction

    function [7:0] frame_byte;
        input [5:0] idx;
        begin
            case (idx)
                6'd0: frame_byte = 8'h02;  // AUTH_RESP
                6'd1: frame_byte = 8'h00;  // LEN high
                6'd2: frame_byte = 8'h26;  // LEN low = 38
                default: begin
                    if (idx >= 6'd3 && idx < 6'd41)
                        frame_byte = resp_byte(idx - 6'd3);
                    else
                        frame_byte = 8'h00;
                end
            endcase
        end
    endfunction

    // -----------------------------------------------------------------------
    // AXI4-Lite master + HMAC IP
    // -----------------------------------------------------------------------
    reg         axi_start;
    reg         axi_wr;
    reg  [7:0]  axi_addr;
    reg  [31:0] axi_wdata;
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

    // -----------------------------------------------------------------------
    // Auth FSM
    // -----------------------------------------------------------------------
    localparam [3:0]
        A_IDLE      = 4'd0,
        A_ADC       = 4'd1,
        A_WR        = 4'd2,
        A_WR_WAIT   = 4'd3,
        A_POLL      = 4'd4,
        A_POLL_WAIT = 4'd5,
        A_RD        = 4'd6,
        A_RD_WAIT   = 4'd7,
        A_TX        = 4'd8,
        A_TX_WAIT   = 4'd9,
        A_ADC_START = 4'd10;

    reg [3:0]  astate;
    reg [4:0]  wr_idx;
    reg [2:0]  rd_idx;
    reg [5:0]  tx_idx;
    reg [7:0]  tx_crc;
    reg        auth_ok;
    reg        auth_error;
    integer    j;

    always @(posedge clk) begin
        if (!resetn) begin
            astate     <= A_IDLE;
            adc_start  <= 1'b0;
            tx_start   <= 1'b0;
            tx_byte    <= 8'd0;
            axi_start  <= 1'b0;
            axi_wr     <= 1'b0;
            axi_addr   <= 8'd0;
            axi_wdata  <= 32'd0;
            wr_idx     <= 5'd0;
            rd_idx     <= 3'd0;
            tx_idx     <= 6'd0;
            tx_crc     <= 8'd0;
            voltage    <= 16'd0;
            auth_ok    <= 1'b0;
            auth_error <= 1'b0;
            for (j = 0; j < 64; j = j + 1)
                msg_bytes[j] <= 8'd0;
            for (j = 0; j < 32; j = j + 1)
                hash_bytes[j] <= 8'd0;
        end else begin
            adc_start <= 1'b0;
            tx_start  <= 1'b0;
            axi_start <= 1'b0;

            if (axi_err)
                auth_error <= 1'b1;

            if (frame_error) begin
                auth_error <= 1'b1;
                auth_ok    <= 1'b0;
            end

            if (frame_valid && !(p_cmd == 8'h01 && p_len == 16'd32)) begin
                auth_error <= 1'b1;
                auth_ok    <= 1'b0;
            end

            case (astate)
                A_IDLE: begin
                    if (frame_valid && p_cmd == 8'h01 && p_len == 16'd32) begin
                        for (j = 0; j < 32; j = j + 1)
                            msg_bytes[j] <= payload[j];
                        msg_bytes[32] <= bid_byte(2'd0);
                        msg_bytes[33] <= bid_byte(2'd1);
                        msg_bytes[34] <= bid_byte(2'd2);
                        msg_bytes[35] <= bid_byte(2'd3);
                        msg_bytes[36] <= 8'd0;
                        msg_bytes[37] <= 8'd0;
                        for (j = 38; j < 64; j = j + 1)
                            msg_bytes[j] <= 8'd0;
                        auth_ok    <= 1'b0;
                        auth_error <= 1'b0;
                        adc_start  <= 1'b1;
                        astate     <= A_ADC_START;
                    end
                end

                // One-cycle bubble: ads1115_ctrl clears its sticky error on
                // the start edge; without this, a stale adc_error would make
                // the new transaction skip the ADC.
                A_ADC_START: begin
                    astate <= A_ADC;
                end

                A_ADC: begin
                    if (adc_valid) begin
                        voltage       <= adc_mv;
                        msg_bytes[36] <= adc_mv[15:8];
                        msg_bytes[37] <= adc_mv[7:0];
                        wr_idx        <= 5'd0;
                        astate        <= A_WR;
                    end else if (adc_error) begin
                        auth_error    <= 1'b1;
                        voltage       <= 16'd0;
                        msg_bytes[36] <= 8'd0;
                        msg_bytes[37] <= 8'd0;
                        wr_idx        <= 5'd0;
                        astate        <= A_WR;
                    end
                end

                A_WR: begin
                    if (!axi_busy) begin
                        axi_wr <= 1'b1;
                        if (wr_idx < 5'd8) begin
                            axi_addr  <= 8'h10 + {wr_idx, 2'b00};
                            axi_wdata <= key_word(wr_idx[2:0]);
                        end else if (wr_idx < 5'd18) begin
                            axi_addr  <= 8'h30 + {(wr_idx - 5'd8), 2'b00};
                            axi_wdata <= msg_word(wr_idx[3:0] - 4'd8);
                        end else if (wr_idx == 5'd18) begin
                            axi_addr  <= 8'h08;
                            axi_wdata <= 32'd38;
                        end else begin
                            axi_addr  <= 8'h00;
                            axi_wdata <= 32'd1;
                        end
                        axi_start <= 1'b1;
                        astate    <= A_WR_WAIT;
                    end
                end

                A_WR_WAIT: begin
                    if (axi_done) begin
                        if (wr_idx == 5'd19) begin
                            astate <= A_POLL;
                        end else begin
                            wr_idx <= wr_idx + 5'd1;
                            astate <= A_WR;
                        end
                    end
                end

                A_POLL: begin
                    if (!axi_busy) begin
                        axi_wr    <= 1'b0;
                        axi_addr  <= 8'h04;
                        axi_start <= 1'b1;
                        astate    <= A_POLL_WAIT;
                    end
                end

                A_POLL_WAIT: begin
                    if (axi_done) begin
                        if (axi_rd_data[0]) begin
                            rd_idx <= 3'd0;
                            astate <= A_RD;
                        end else begin
                            astate <= A_POLL;
                        end
                    end
                end

                A_RD: begin
                    if (!axi_busy) begin
                        axi_wr    <= 1'b0;
                        axi_addr  <= 8'h70 + {rd_idx, 2'b00};
                        axi_start <= 1'b1;
                        astate    <= A_RD_WAIT;
                    end
                end

                A_RD_WAIT: begin
                    if (axi_done) begin
                        hash_bytes[{rd_idx, 2'b00}]       <= axi_rd_data[31:24];
                        hash_bytes[{rd_idx, 2'b00} + 6'd1] <= axi_rd_data[23:16];
                        hash_bytes[{rd_idx, 2'b00} + 6'd2] <= axi_rd_data[15:8];
                        hash_bytes[{rd_idx, 2'b00} + 6'd3] <= axi_rd_data[7:0];
                        if (rd_idx == 3'd7) begin
                            tx_idx <= 6'd0;
                            tx_crc <= 8'd0;
                            astate <= A_TX;
                        end else begin
                            rd_idx <= rd_idx + 3'd1;
                            astate <= A_RD;
                        end
                    end
                end

                A_TX: begin
                    if (tx_idx < 6'd42) begin
                        if (tx_idx < 6'd41)
                            tx_byte <= frame_byte(tx_idx);
                        else
                            tx_byte <= tx_crc;
                        tx_start <= 1'b1;
                        astate   <= A_TX_WAIT;
                    end else begin
                        auth_ok <= 1'b1;
                        astate  <= A_IDLE;
                    end
                end

                A_TX_WAIT: begin
                    if (tx_done) begin
                        if (tx_idx < 6'd41)
                            tx_crc <= crc8_byte(tx_crc, frame_byte(tx_idx));
                        tx_idx <= tx_idx + 6'd1;
                        astate <= A_TX;
                    end
                end

                default: astate <= A_IDLE;
            endcase
        end
    end

    // -----------------------------------------------------------------------
    // LEDs: heartbeat, busy, last auth ok, last auth error
    // -----------------------------------------------------------------------
    reg [23:0] hb_cnt;

    always @(posedge clk) begin
        if (!resetn) begin
            hb_cnt <= 24'd0;
            led    <= 4'd0;
        end else begin
            hb_cnt <= hb_cnt + 24'd1;
            led[0] <= hb_cnt[23];
            led[1] <= (astate != A_IDLE) || adc_busy || axi_busy || tx_busy;
            led[2] <= auth_ok;
            led[3] <= auth_error;
        end
    end

endmodule
