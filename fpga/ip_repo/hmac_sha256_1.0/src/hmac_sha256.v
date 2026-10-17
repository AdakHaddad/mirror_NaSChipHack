// ===========================================================================
//  hmac_sha256.v — HMAC-SHA-256 with AXI4-Lite slave interface
//  SeBatt project — Hackathon Deeptech 2026
//
//  HMAC(K, m) = SHA256( (K ^ opad) || SHA256( (K ^ ipad) || m ) )
//
//  For SeBatt: message = nonce(32) + battery_id(4) + voltage(2) = 38 bytes
//  Padded to 1 SHA-256 block. HMAC needs 4 SHA-256 blocks total:
//    1. K ^ ipad  (64B)
//    2. msg + pad (64B)   → inner_hash
//    3. K ^ opad  (64B)
//    4. inner_hash + pad (64B) → HMAC
//
//  AXI4-Lite register map:
//    0x00  CTRL    R/W  [0]=start(WO,auto-clear) [1]=init(WO,auto-clear)
//    0x04  STATUS  RO   [0]=done [1]=busy
//    0x08  MSG_LEN R/W  message length in bytes
//    0x10–0x2C  KEY[0..7]   R/W  256-bit key
//    0x30–0x6C  MSG[0..15]  R/W  message (up to 64B, 1 block)
//    0x70–0x8C  HASH[0..7]  RO   256-bit HMAC result
// ===========================================================================

module hmac_sha256 #(
    parameter C_S_AXI_DATA_WIDTH = 32,
    parameter C_S_AXI_ADDR_WIDTH = 8
)(
    input  wire                               s_axi_aclk,
    input  wire                               s_axi_aresetn,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]      s_axi_awaddr,
    input  wire [2:0]                         s_axi_awprot,
    input  wire                               s_axi_awvalid,
    output reg                                s_axi_awready,
    input  wire [C_S_AXI_DATA_WIDTH-1:0]      s_axi_wdata,
    input  wire [C_S_AXI_DATA_WIDTH/8-1:0]    s_axi_wstrb,
    input  wire                               s_axi_wvalid,
    output reg                                s_axi_wready,
    output reg  [1:0]                         s_axi_bresp,
    output reg                                s_axi_bvalid,
    input  wire                               s_axi_bready,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]      s_axi_araddr,
    input  wire [2:0]                         s_axi_arprot,
    input  wire                               s_axi_arvalid,
    output reg                                s_axi_arready,
    output reg  [C_S_AXI_DATA_WIDTH-1:0]      s_axi_rdata,
    output reg  [1:0]                         s_axi_rresp,
    output reg                                s_axi_rvalid,
    input  wire                               s_axi_rready
);

    // -----------------------------------------------------------------------
    // Registers
    // -----------------------------------------------------------------------
    reg [31:0] key_reg  [0:7];
    reg [31:0] msg_reg  [0:15];
    reg [31:0] hash_reg [0:7];
    reg [31:0] msg_len;

    // -----------------------------------------------------------------------
    // SHA-256 core
    // -----------------------------------------------------------------------
    reg         sha_init;
    reg         sha_start;
    reg [31:0]  sha_word;
    reg         sha_we;
    reg [3:0]   sha_addr;
    wire        sha_done;
    wire        sha_ready;
    wire [255:0] sha_hash;

    sha256_core u_sha (
        .clk        (s_axi_aclk),
        .rst_n      (s_axi_aresetn),
        .init_i     (sha_init),
        .start_i    (sha_start),
        .done_o     (sha_done),
        .ready_o    (sha_ready),
        .msg_word_i (sha_word),
        .msg_we_i   (sha_we),
        .msg_addr_i (sha_addr),
        .hash_o     (sha_hash)
    );

    // -----------------------------------------------------------------------
    // HMAC FSM
    // -----------------------------------------------------------------------
    localparam H_IDLE       = 4'd0;
    localparam H_INIT_INNER = 4'd1;  // sha_init for inner hash
    localparam H_LOAD_IPAD  = 4'd2;  // load K^ipad block
    localparam H_RUN_IPAD   = 4'd3;  // start + wait sha
    localparam H_LOAD_MSG   = 4'd4;  // load message+padding block
    localparam H_RUN_MSG    = 4'd5;  // start + wait sha → inner hash
    localparam H_INIT_OUTER = 4'd6;  // sha_init for outer hash
    localparam H_LOAD_OPAD  = 4'd7;  // load K^opad block
    localparam H_RUN_OPAD   = 4'd8;  // start + wait sha
    localparam H_LOAD_FINAL = 4'd9;  // load inner_hash+padding
    localparam H_RUN_FINAL  = 4'd10; // start + wait sha → HMAC
    localparam H_DONE       = 4'd11;

    reg [3:0]  hstate;
    reg        hmac_busy;
    reg        hmac_done;
    reg [4:0]  lcnt;             // load counter 0–15
    reg        sha_started;      // track if sha_start was pulsed
    reg [31:0] inner [0:7];      // inner hash storage

    // Control signals from AXI writes
    reg ctrl_start;
    reg ctrl_init;

    // -----------------------------------------------------------------------
    // HMAC FSM
    // -----------------------------------------------------------------------
    always @(posedge s_axi_aclk or negedge s_axi_aresetn) begin
        if (!s_axi_aresetn) begin
            hstate      <= H_IDLE;
            hmac_busy   <= 1'b0;
            hmac_done   <= 1'b0;
            sha_init    <= 1'b0;
            sha_start   <= 1'b0;
            sha_we      <= 1'b0;
            sha_word    <= 32'd0;
            sha_addr    <= 4'd0;
            lcnt        <= 5'd0;
            sha_started <= 1'b0;
        end else begin
            // Defaults
            sha_init  <= 1'b0;
            sha_start <= 1'b0;
            sha_we    <= 1'b0;

            case (hstate)
                H_IDLE: begin
                    if (ctrl_start && !hmac_busy) begin
                        hmac_busy <= 1'b1;
                        hmac_done <= 1'b0;
                        hstate    <= H_INIT_INNER;
                    end
                    if (ctrl_init)
                        hmac_done <= 1'b0;
                end

                // --- Inner hash: SHA(K^ipad || msg) ---
                H_INIT_INNER: begin
                    sha_init <= 1'b1;
                    lcnt     <= 5'd0;
                    hstate   <= H_LOAD_IPAD;
                end

                H_LOAD_IPAD: begin
                    if (sha_ready) begin
                        sha_we   <= 1'b1;
                        sha_addr <= lcnt[3:0];
                        if (lcnt < 5'd8)
                            sha_word <= key_reg[lcnt[2:0]] ^ 32'h36363636;
                        else
                            sha_word <= 32'h36363636;  // 0x00 ^ 0x36

                        if (lcnt == 5'd15) begin
                            lcnt        <= 5'd0;
                            sha_started <= 1'b0;
                            hstate      <= H_RUN_IPAD;
                        end else begin
                            lcnt <= lcnt + 5'd1;
                        end
                    end
                end

                H_RUN_IPAD: begin
                    if (!sha_started && sha_ready) begin
                        sha_start   <= 1'b1;
                        sha_started <= 1'b1;
                    end
                    if (sha_done) begin
                        lcnt        <= 5'd0;
                        sha_started <= 1'b0;
                        hstate      <= H_LOAD_MSG;
                    end
                end

                H_LOAD_MSG: begin
                    // Load message with SHA-256 padding into one 64-byte block.
                    // msg_len must be ≤ 55 for single-block padding.
                    // Layout: msg_bytes | 0x80 | zeros | 64-bit bit-length
                    // Bit length = (64 + msg_len) * 8  (ipad block + this block)
                    if (sha_ready) begin
                        sha_we   <= 1'b1;
                        sha_addr <= lcnt[3:0];

                        begin : msg_pad_logic
                            reg [5:0] full_words;  // msg_len / 4
                            reg [1:0] tail_bytes;  // msg_len % 4
                            full_words = msg_len[5:2];
                            tail_bytes = msg_len[1:0];

                            if (lcnt < {1'b0, full_words}) begin
                                // Full message words
                                sha_word <= msg_reg[lcnt[3:0]];
                            end else if (lcnt == {1'b0, full_words} && tail_bytes != 2'd0) begin
                                // Partial word: tail_bytes of data + 0x80
                                case (tail_bytes)
                                    2'd1: sha_word <= {msg_reg[lcnt[3:0]][31:24], 8'h80, 16'h0000};
                                    2'd2: sha_word <= {msg_reg[lcnt[3:0]][31:16], 8'h80, 8'h00};
                                    2'd3: sha_word <= {msg_reg[lcnt[3:0]][31:8],  8'h80};
                                    default: sha_word <= 32'h80000000;
                                endcase
                            end else if (lcnt == {1'b0, full_words} && tail_bytes == 2'd0) begin
                                // Exact word boundary: 0x80 starts next word
                                sha_word <= 32'h80000000;
                            end else if (lcnt == 5'd14) begin
                                sha_word <= 32'h00000000;
                            end else if (lcnt == 5'd15) begin
                                sha_word <= (32'd64 + msg_len) << 3;
                            end else begin
                                sha_word <= 32'h00000000;
                            end
                        end

                        if (lcnt == 5'd15) begin
                            lcnt        <= 5'd0;
                            sha_started <= 1'b0;
                            hstate      <= H_RUN_MSG;
                        end else begin
                            lcnt <= lcnt + 5'd1;
                        end
                    end
                end

                H_RUN_MSG: begin
                    if (!sha_started && sha_ready) begin
                        sha_start   <= 1'b1;
                        sha_started <= 1'b1;
                    end
                    if (sha_done) begin
                        // Save inner hash
                        inner[0] <= sha_hash[255:224];
                        inner[1] <= sha_hash[223:192];
                        inner[2] <= sha_hash[191:160];
                        inner[3] <= sha_hash[159:128];
                        inner[4] <= sha_hash[127:96];
                        inner[5] <= sha_hash[95:64];
                        inner[6] <= sha_hash[63:32];
                        inner[7] <= sha_hash[31:0];
                        sha_started <= 1'b0;
                        hstate      <= H_INIT_OUTER;
                    end
                end

                // --- Outer hash: SHA(K^opad || inner_hash) ---
                H_INIT_OUTER: begin
                    sha_init <= 1'b1;
                    lcnt     <= 5'd0;
                    hstate   <= H_LOAD_OPAD;
                end

                H_LOAD_OPAD: begin
                    if (sha_ready) begin
                        sha_we   <= 1'b1;
                        sha_addr <= lcnt[3:0];
                        if (lcnt < 5'd8)
                            sha_word <= key_reg[lcnt[2:0]] ^ 32'h5c5c5c5c;
                        else
                            sha_word <= 32'h5c5c5c5c;

                        if (lcnt == 5'd15) begin
                            lcnt        <= 5'd0;
                            sha_started <= 1'b0;
                            hstate      <= H_RUN_OPAD;
                        end else begin
                            lcnt <= lcnt + 5'd1;
                        end
                    end
                end

                H_RUN_OPAD: begin
                    if (!sha_started && sha_ready) begin
                        sha_start   <= 1'b1;
                        sha_started <= 1'b1;
                    end
                    if (sha_done) begin
                        lcnt        <= 5'd0;
                        sha_started <= 1'b0;
                        hstate      <= H_LOAD_FINAL;
                    end
                end

                H_LOAD_FINAL: begin
                    // Load inner_hash(32B) + 0x80 + zeros + length
                    // Length = (64+32)*8 = 768 = 0x300
                    if (sha_ready) begin
                        sha_we   <= 1'b1;
                        sha_addr <= lcnt[3:0];

                        if (lcnt < 5'd8)
                            sha_word <= inner[lcnt[2:0]];
                        else if (lcnt == 5'd8)
                            sha_word <= 32'h80000000;
                        else if (lcnt == 5'd14)
                            sha_word <= 32'h0;
                        else if (lcnt == 5'd15)
                            sha_word <= 32'h00000300;  // 768 bits
                        else
                            sha_word <= 32'h0;

                        if (lcnt == 5'd15) begin
                            lcnt        <= 5'd0;
                            sha_started <= 1'b0;
                            hstate      <= H_RUN_FINAL;
                        end else begin
                            lcnt <= lcnt + 5'd1;
                        end
                    end
                end

                H_RUN_FINAL: begin
                    if (!sha_started && sha_ready) begin
                        sha_start   <= 1'b1;
                        sha_started <= 1'b1;
                    end
                    if (sha_done) begin
                        hash_reg[0] <= sha_hash[255:224];
                        hash_reg[1] <= sha_hash[223:192];
                        hash_reg[2] <= sha_hash[191:160];
                        hash_reg[3] <= sha_hash[159:128];
                        hash_reg[4] <= sha_hash[127:96];
                        hash_reg[5] <= sha_hash[95:64];
                        hash_reg[6] <= sha_hash[63:32];
                        hash_reg[7] <= sha_hash[31:0];
                        hstate      <= H_DONE;
                    end
                end

                H_DONE: begin
                    hmac_done <= 1'b1;
                    hmac_busy <= 1'b0;
                    hstate    <= H_IDLE;
                end

                default: hstate <= H_IDLE;
            endcase
        end
    end

    // -----------------------------------------------------------------------
    // AXI4-Lite write
    // -----------------------------------------------------------------------
    reg [C_S_AXI_ADDR_WIDTH-1:0] awaddr_r;

    always @(posedge s_axi_aclk or negedge s_axi_aresetn) begin
        if (!s_axi_aresetn) begin
            s_axi_awready <= 1'b0;
            awaddr_r      <= 0;
        end else begin
            if (~s_axi_awready && s_axi_awvalid && s_axi_wvalid) begin
                s_axi_awready <= 1'b1;
                awaddr_r      <= s_axi_awaddr;
            end else
                s_axi_awready <= 1'b0;
        end
    end

    always @(posedge s_axi_aclk or negedge s_axi_aresetn) begin
        if (!s_axi_aresetn)
            s_axi_wready <= 1'b0;
        else if (~s_axi_wready && s_axi_wvalid && s_axi_awvalid)
            s_axi_wready <= 1'b1;
        else
            s_axi_wready <= 1'b0;
    end

    always @(posedge s_axi_aclk or negedge s_axi_aresetn) begin
        if (!s_axi_aresetn) begin
            s_axi_bvalid <= 1'b0;
            s_axi_bresp  <= 2'b00;
        end else if (s_axi_awready && s_axi_awvalid && s_axi_wready && s_axi_wvalid && ~s_axi_bvalid) begin
            s_axi_bvalid <= 1'b1;
            s_axi_bresp  <= 2'b00;
        end else if (s_axi_bready && s_axi_bvalid)
            s_axi_bvalid <= 1'b0;
    end

    wire wr_en = s_axi_awready && s_axi_awvalid && s_axi_wready && s_axi_wvalid;

    always @(posedge s_axi_aclk or negedge s_axi_aresetn) begin
        if (!s_axi_aresetn) begin
            ctrl_start <= 1'b0;
            ctrl_init  <= 1'b0;
            msg_len    <= 32'd38;
            begin : wr_rst
                integer i;
                for (i = 0; i < 8;  i = i+1) key_reg[i] <= 32'd0;
                for (i = 0; i < 16; i = i+1) msg_reg[i] <= 32'd0;
            end
        end else begin
            ctrl_start <= 1'b0;
            ctrl_init  <= 1'b0;
            if (wr_en) begin
                case (awaddr_r)
                    8'h00: begin ctrl_start <= s_axi_wdata[0]; ctrl_init <= s_axi_wdata[1]; end
                    8'h08: msg_len <= s_axi_wdata;
                    8'h10: key_reg[0]  <= s_axi_wdata;
                    8'h14: key_reg[1]  <= s_axi_wdata;
                    8'h18: key_reg[2]  <= s_axi_wdata;
                    8'h1C: key_reg[3]  <= s_axi_wdata;
                    8'h20: key_reg[4]  <= s_axi_wdata;
                    8'h24: key_reg[5]  <= s_axi_wdata;
                    8'h28: key_reg[6]  <= s_axi_wdata;
                    8'h2C: key_reg[7]  <= s_axi_wdata;
                    8'h30: msg_reg[0]  <= s_axi_wdata;
                    8'h34: msg_reg[1]  <= s_axi_wdata;
                    8'h38: msg_reg[2]  <= s_axi_wdata;
                    8'h3C: msg_reg[3]  <= s_axi_wdata;
                    8'h40: msg_reg[4]  <= s_axi_wdata;
                    8'h44: msg_reg[5]  <= s_axi_wdata;
                    8'h48: msg_reg[6]  <= s_axi_wdata;
                    8'h4C: msg_reg[7]  <= s_axi_wdata;
                    8'h50: msg_reg[8]  <= s_axi_wdata;
                    8'h54: msg_reg[9]  <= s_axi_wdata;
                    8'h58: msg_reg[10] <= s_axi_wdata;
                    8'h5C: msg_reg[11] <= s_axi_wdata;
                    8'h60: msg_reg[12] <= s_axi_wdata;
                    8'h64: msg_reg[13] <= s_axi_wdata;
                    8'h68: msg_reg[14] <= s_axi_wdata;
                    8'h6C: msg_reg[15] <= s_axi_wdata;
                    default: ;
                endcase
            end
        end
    end

    // -----------------------------------------------------------------------
    // AXI4-Lite read
    // -----------------------------------------------------------------------
    always @(posedge s_axi_aclk or negedge s_axi_aresetn) begin
        if (!s_axi_aresetn) begin
            s_axi_arready <= 1'b0;
            s_axi_rvalid  <= 1'b0;
            s_axi_rresp   <= 2'b00;
        end else begin
            if (~s_axi_arready && s_axi_arvalid)
                s_axi_arready <= 1'b1;
            else
                s_axi_arready <= 1'b0;

            if (s_axi_arready && s_axi_arvalid && ~s_axi_rvalid) begin
                s_axi_rvalid <= 1'b1;
                s_axi_rresp  <= 2'b00;
            end else if (s_axi_rvalid && s_axi_rready)
                s_axi_rvalid <= 1'b0;
        end
    end

    always @(posedge s_axi_aclk) begin
        if (s_axi_arready && s_axi_arvalid && ~s_axi_rvalid) begin
            case (s_axi_araddr)
                8'h00: s_axi_rdata <= {28'd0, hmac_done, hmac_busy, 2'b00};
                8'h04: s_axi_rdata <= {30'd0, hmac_busy, hmac_done};
                8'h08: s_axi_rdata <= msg_len;
                8'h10: s_axi_rdata <= key_reg[0];
                8'h14: s_axi_rdata <= key_reg[1];
                8'h18: s_axi_rdata <= key_reg[2];
                8'h1C: s_axi_rdata <= key_reg[3];
                8'h20: s_axi_rdata <= key_reg[4];
                8'h24: s_axi_rdata <= key_reg[5];
                8'h28: s_axi_rdata <= key_reg[6];
                8'h2C: s_axi_rdata <= key_reg[7];
                8'h70: s_axi_rdata <= hash_reg[0];
                8'h74: s_axi_rdata <= hash_reg[1];
                8'h78: s_axi_rdata <= hash_reg[2];
                8'h7C: s_axi_rdata <= hash_reg[3];
                8'h80: s_axi_rdata <= hash_reg[4];
                8'h84: s_axi_rdata <= hash_reg[5];
                8'h88: s_axi_rdata <= hash_reg[6];
                8'h8C: s_axi_rdata <= hash_reg[7];
                default: s_axi_rdata <= 32'd0;
            endcase
        end
    end

endmodule
