// ===========================================================================
//  key_vault.v — Fixed key store (Stage 1)
//  SeBatt project — Hackathon Deeptech 2026
//
//  Stores a 256-bit fixed key. Read via 8x 32-bit word reads.
//  Stage 2: replace with ro_puf + fuzzy_ext output.
//
//  Default key = 0x000102...1F (bytes(range(32))) — matches Python model.
// ===========================================================================

module key_vault (
    input  wire         clk,
    input  wire         rst_n,

    // Key read interface
    input  wire [2:0]   addr_i,       // Word address 0–7
    output reg  [31:0]  data_o,       // Key word

    // Key write interface (for testing / PUF enrollment)
    input  wire [2:0]   wr_addr_i,
    input  wire [31:0]  wr_data_i,
    input  wire         wr_en_i,

    // Full key output (for direct connection to HMAC)
    output wire [255:0] key_o
);

    reg [31:0] key_mem [0:7];

    assign key_o = {key_mem[0], key_mem[1], key_mem[2], key_mem[3],
                    key_mem[4], key_mem[5], key_mem[6], key_mem[7]};

    // Default key initialization
    integer i;
    initial begin
        // key = bytes(range(32)) = 0x00010203 04050607 ... 1c1d1e1f
        key_mem[0] = 32'h00010203;
        key_mem[1] = 32'h04050607;
        key_mem[2] = 32'h08090a0b;
        key_mem[3] = 32'h0c0d0e0f;
        key_mem[4] = 32'h10111213;
        key_mem[5] = 32'h14151617;
        key_mem[6] = 32'h18191a1b;
        key_mem[7] = 32'h1c1d1e1f;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            key_mem[0] <= 32'h00010203;
            key_mem[1] <= 32'h04050607;
            key_mem[2] <= 32'h08090a0b;
            key_mem[3] <= 32'h0c0d0e0f;
            key_mem[4] <= 32'h10111213;
            key_mem[5] <= 32'h14151617;
            key_mem[6] <= 32'h18191a1b;
            key_mem[7] <= 32'h1c1d1e1f;
        end else begin
            if (wr_en_i) begin
                key_mem[wr_addr_i] <= wr_data_i;
            end
        end
    end

    // Combinational read
    always @(*) begin
        data_o = key_mem[addr_i];
    end

endmodule
