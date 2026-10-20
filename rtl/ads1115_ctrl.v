// ===========================================================================
//  ads1115_ctrl.v — ADS1115 single-shot reader
//  SeBatt project — Hackathon Deeptech 2026
//
//  Sequence on start:
//    1. Write config 0xC383 to reg 0x01
//         OS=1, MUX=100 (AIN0 vs GND), PGA=001 (±4.096 V),
//         MODE=1 (single-shot), DR=100 (128 SPS), comparator off.
//    2. Wait CONV_CYCLES (default 10 ms; 128 SPS needs 7.8 ms).
//    3. Read reg 0x00 (16-bit conversion).
//
//  mV = raw / 8 (LSB = 0.125 mV with PGA ±4.096 V).
//  AIN0 is single-ended, so a negative raw value is clamped to 0.
// ===========================================================================

module ads1115_ctrl #(
    parameter integer CLK_HZ = 100_000_000,
    parameter integer I2C_HZ = 100_000,
`ifdef SIMULATION
    // Short conversion wait so the cocotb test runs in a few ms of sim time.
    parameter integer CONV_CYCLES = 2000
`else
    // 10 ms: 128 SPS needs 7.8 ms.
    parameter integer CONV_CYCLES = CLK_HZ / 100
`endif
)(
    input  wire        clk,
    input  wire        resetn,
    input  wire        start,        // one-cycle pulse
    output reg  [15:0] raw,
    output reg  [15:0] mv,
    output reg         valid,        // one-cycle pulse on new sample
    output reg         busy,
    output reg         error,        // sticky until the next start
    inout  wire        scl,
    inout  wire        sda
);

    localparam [1:0]
        ST_IDLE = 2'd0,
        ST_WR   = 2'd1,
        ST_WAIT = 2'd2,
        ST_RD   = 2'd3;

    reg [1:0]  state;
    reg [31:0] wait_cnt;

    reg        i2c_start;
    reg        i2c_wr_en;
    reg [7:0]  i2c_reg;
    reg [15:0] i2c_wr_data;

    wire        i2c_done;
    wire        i2c_ack_error;
    wire [15:0] i2c_rd_data;

    i2c_master #(
        .CLK_HZ (CLK_HZ),
        .I2C_HZ (I2C_HZ)
    ) i2c (
        .clk       (clk),
        .resetn    (resetn),
        .start     (i2c_start),
        .dev_addr  (7'h48),
        .reg_addr  (i2c_reg),
        .wr_en     (i2c_wr_en),
        .wr_data   (i2c_wr_data),
        .rd_data   (i2c_rd_data),
        .done      (i2c_done),
        .ack_error (i2c_ack_error),
        .scl       (scl),
        .sda       (sda)
    );

    always @(posedge clk) begin
        if (!resetn) begin
            state       <= ST_IDLE;
            wait_cnt    <= 32'd0;
            i2c_start   <= 1'b0;
            i2c_wr_en   <= 1'b0;
            i2c_reg     <= 8'd0;
            i2c_wr_data <= 16'd0;
            raw         <= 16'd0;
            mv          <= 16'd0;
            valid       <= 1'b0;
            busy        <= 1'b0;
            error       <= 1'b0;
        end else begin
            valid <= 1'b0;

            case (state)
                ST_IDLE: begin
                    if (start) begin
                        busy        <= 1'b1;
                        error       <= 1'b0;
                        i2c_reg     <= 8'h01;
                        i2c_wr_en   <= 1'b1;
                        i2c_wr_data <= 16'hC383;
                        i2c_start   <= 1'b1;
                        state       <= ST_WR;
                    end
                end

                ST_WR: begin
                    i2c_start <= 1'b0;
                    if (i2c_done) begin
                        if (i2c_ack_error) begin
                            error <= 1'b1;
                            busy  <= 1'b0;
                            state <= ST_IDLE;
                        end else begin
                            wait_cnt <= CONV_CYCLES;
                            state    <= ST_WAIT;
                        end
                    end
                end

                ST_WAIT: begin
                    if (wait_cnt == 32'd0) begin
                        i2c_reg   <= 8'h00;
                        i2c_wr_en <= 1'b0;
                        i2c_start <= 1'b1;
                        state     <= ST_RD;
                    end else begin
                        wait_cnt <= wait_cnt - 1'b1;
                    end
                end

                ST_RD: begin
                    i2c_start <= 1'b0;
                    if (i2c_done) begin
                        if (i2c_ack_error) begin
                            error <= 1'b1;
                        end else begin
                            raw   <= i2c_rd_data;
                            mv    <= i2c_rd_data[15] ? 16'd0 : (i2c_rd_data >> 3);
                            valid <= 1'b1;
                        end
                        busy  <= 1'b0;
                        state <= ST_IDLE;
                    end
                end

                default: state <= ST_IDLE;
            endcase
        end
    end

endmodule
