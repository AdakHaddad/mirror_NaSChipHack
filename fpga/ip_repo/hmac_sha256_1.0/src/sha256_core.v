// ===========================================================================
//  sha256_core.v — SHA-256 compression engine
//  SeBatt project — Hackathon Deeptech 2026
//
//  Two-phase pipeline per block:
//    Phase 1 (S_EXPAND): expand W[16..63] from W[0..15], 1 word/cycle (48 cyc)
//    Phase 2 (S_ROUND):  64 compression rounds, 1 round/cycle (64 cyc)
//    S_DONE: add working vars to hash state (1 cyc)
//  Total: 113 cycles per block. 4 blocks for HMAC = 452 cycles.
//
//  Interface:
//    - Load W[0..15] via msg_word_i / msg_addr_i / msg_we_i while ready_o=1
//    - Assert start_i → expansion + compression begins
//    - done_o pulses when hash is updated
//    - hash_o valid after done_o until next init_i or start_i
//    - init_i resets hash to H_INIT for new message
// ===========================================================================

module sha256_core (
    input  wire         clk,
    input  wire         rst_n,

    input  wire         init_i,
    input  wire         start_i,
    output reg          done_o,
    output wire         ready_o,

    input  wire [31:0]  msg_word_i,
    input  wire         msg_we_i,
    input  wire [3:0]   msg_addr_i,

    output wire [255:0] hash_o
);

    // -----------------------------------------------------------------------
    // K constants
    // -----------------------------------------------------------------------
    function [31:0] K;
        input [5:0] idx;
        case (idx)
            6'd0 : K = 32'h428a2f98;  6'd1 : K = 32'h71374491;
            6'd2 : K = 32'hb5c0fbcf;  6'd3 : K = 32'he9b5dba5;
            6'd4 : K = 32'h3956c25b;  6'd5 : K = 32'h59f111f1;
            6'd6 : K = 32'h923f82a4;  6'd7 : K = 32'hab1c5ed5;
            6'd8 : K = 32'hd807aa98;  6'd9 : K = 32'h12835b01;
            6'd10: K = 32'h243185be;  6'd11: K = 32'h550c7dc3;
            6'd12: K = 32'h72be5d74;  6'd13: K = 32'h80deb1fe;
            6'd14: K = 32'h9bdc06a7;  6'd15: K = 32'hc19bf174;
            6'd16: K = 32'he49b69c1;  6'd17: K = 32'hefbe4786;
            6'd18: K = 32'h0fc19dc6;  6'd19: K = 32'h240ca1cc;
            6'd20: K = 32'h2de92c6f;  6'd21: K = 32'h4a7484aa;
            6'd22: K = 32'h5cb0a9dc;  6'd23: K = 32'h76f988da;
            6'd24: K = 32'h983e5152;  6'd25: K = 32'ha831c66d;
            6'd26: K = 32'hb00327c8;  6'd27: K = 32'hbf597fc7;
            6'd28: K = 32'hc6e00bf3;  6'd29: K = 32'hd5a79147;
            6'd30: K = 32'h06ca6351;  6'd31: K = 32'h14292967;
            6'd32: K = 32'h27b70a85;  6'd33: K = 32'h2e1b2138;
            6'd34: K = 32'h4d2c6dfc;  6'd35: K = 32'h53380d13;
            6'd36: K = 32'h650a7354;  6'd37: K = 32'h766a0abb;
            6'd38: K = 32'h81c2c92e;  6'd39: K = 32'h92722c85;
            6'd40: K = 32'ha2bfe8a1;  6'd41: K = 32'ha81a664b;
            6'd42: K = 32'hc24b8b70;  6'd43: K = 32'hc76c51a3;
            6'd44: K = 32'hd192e819;  6'd45: K = 32'hd6990624;
            6'd46: K = 32'hf40e3585;  6'd47: K = 32'h106aa070;
            6'd48: K = 32'h19a4c116;  6'd49: K = 32'h1e376c08;
            6'd50: K = 32'h2748774c;  6'd51: K = 32'h34b0bcb5;
            6'd52: K = 32'h391c0cb3;  6'd53: K = 32'h4ed8aa4a;
            6'd54: K = 32'h5b9cca4f;  6'd55: K = 32'h682e6ff3;
            6'd56: K = 32'h748f82ee;  6'd57: K = 32'h78a5636f;
            6'd58: K = 32'h84c87814;  6'd59: K = 32'h8cc70208;
            6'd60: K = 32'h90befffa;  6'd61: K = 32'ha4506ceb;
            6'd62: K = 32'hbef9a3f7;  6'd63: K = 32'hc67178f2;
            default: K = 32'h0;
        endcase
    endfunction

    // -----------------------------------------------------------------------
    // Subfunctions
    // -----------------------------------------------------------------------
    function [31:0] rotr;
        input [31:0] x; input [4:0] n;
        rotr = (x >> n) | (x << (32 - n));
    endfunction
    function [31:0] sigma0; input [31:0] x;
        sigma0 = rotr(x,5'd2) ^ rotr(x,5'd13) ^ rotr(x,5'd22);
    endfunction
    function [31:0] sigma1; input [31:0] x;
        sigma1 = rotr(x,5'd6) ^ rotr(x,5'd11) ^ rotr(x,5'd25);
    endfunction
    function [31:0] gamma0; input [31:0] x;
        gamma0 = rotr(x,5'd7) ^ rotr(x,5'd18) ^ (x >> 3);
    endfunction
    function [31:0] gamma1; input [31:0] x;
        gamma1 = rotr(x,5'd17) ^ rotr(x,5'd19) ^ (x >> 10);
    endfunction
    function [31:0] ch; input [31:0] x,y,z;
        ch = (x & y) ^ (~x & z);
    endfunction
    function [31:0] maj; input [31:0] x,y,z;
        maj = (x & y) ^ (x & z) ^ (y & z);
    endfunction

    // -----------------------------------------------------------------------
    // State machine
    // -----------------------------------------------------------------------
    localparam S_IDLE   = 2'd0;
    localparam S_EXPAND = 2'd1;
    localparam S_ROUND  = 2'd2;
    localparam S_DONE   = 2'd3;

    reg [1:0]  state;
    reg [5:0]  cnt;          // expansion counter 16..63, then round counter 0..63

    // W schedule — 64 words
    reg [31:0] w [0:63];

    // Working variables
    reg [31:0] va, vb, vc, vd, ve, vf, vg, vh;

    // Hash state
    reg [31:0] h0, h1, h2, h3, h4, h5, h6, h7;

    assign ready_o = (state == S_IDLE);
    assign hash_o  = {h0, h1, h2, h3, h4, h5, h6, h7};

    // -----------------------------------------------------------------------
    // FSM
    // -----------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state  <= S_IDLE;
            cnt    <= 6'd0;
            done_o <= 1'b0;
            h0 <= 32'h6a09e667; h1 <= 32'hbb67ae85;
            h2 <= 32'h3c6ef372; h3 <= 32'ha54ff53a;
            h4 <= 32'h510e527f; h5 <= 32'h9b05688c;
            h6 <= 32'h1f83d9ab; h7 <= 32'h5be0cd19;
        end else begin
            done_o <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (msg_we_i)
                        w[msg_addr_i] <= msg_word_i;

                    if (init_i) begin
                        h0 <= 32'h6a09e667; h1 <= 32'hbb67ae85;
                        h2 <= 32'h3c6ef372; h3 <= 32'ha54ff53a;
                        h4 <= 32'h510e527f; h5 <= 32'h9b05688c;
                        h6 <= 32'h1f83d9ab; h7 <= 32'h5be0cd19;
                    end

                    if (start_i) begin
                        cnt   <= 6'd16;
                        state <= S_EXPAND;
                    end
                end

                S_EXPAND: begin
                    // Compute W[cnt] = gamma1(W[cnt-2]) + W[cnt-7]
                    //                + gamma0(W[cnt-15]) + W[cnt-16]
                    w[cnt] <= gamma1(w[cnt-2]) + w[cnt-7]
                            + gamma0(w[cnt-15]) + w[cnt-16];

                    if (cnt == 6'd63) begin
                        // Init working variables
                        va <= h0; vb <= h1; vc <= h2; vd <= h3;
                        ve <= h4; vf <= h5; vg <= h6; vh <= h7;
                        cnt   <= 6'd0;
                        state <= S_ROUND;
                    end else begin
                        cnt <= cnt + 6'd1;
                    end
                end

                S_ROUND: begin
                    begin : compress
                        reg [31:0] t1, t2;
                        t1 = vh + sigma1(ve) + ch(ve,vf,vg) + K(cnt) + w[cnt];
                        t2 = sigma0(va) + maj(va,vb,vc);
                        vh <= vg;
                        vg <= vf;
                        vf <= ve;
                        ve <= vd + t1;
                        vd <= vc;
                        vc <= vb;
                        vb <= va;
                        va <= t1 + t2;
                    end

                    if (cnt == 6'd63)
                        state <= S_DONE;
                    cnt <= cnt + 6'd1;
                end

                S_DONE: begin
                    h0 <= h0 + va; h1 <= h1 + vb;
                    h2 <= h2 + vc; h3 <= h3 + vd;
                    h4 <= h4 + ve; h5 <= h5 + vf;
                    h6 <= h6 + vg; h7 <= h7 + vh;
                    done_o <= 1'b1;
                    state  <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
