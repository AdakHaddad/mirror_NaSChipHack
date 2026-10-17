// ===========================================================================
//  ro_puf.v — Ring-Oscillator Physical Unclonable Function (Stage 2)
//  SeBatt project — Hackathon Deeptech 2026
//
//  Architecture:
//    - NUM_RO pairs of ring oscillators
//    - Each RO is an odd-inverter loop enabled by ro_en
//    - Measured during fixed count window (e.g. 1024 system clock cycles)
//    - Pairwise frequency comparison: count[2*i] > count[2*i+1] -> bit = 1
//    - Generates RAW_BITS response bits
//
//  Simulation vs Synthesis:
//    - Simulation: behavioral delay model with parameter seeds
//    - Synthesis: (* DONT_TOUCH = "TRUE" *) inverters to prevent logic trimming
// ===========================================================================

`timescale 1ns / 1ps

module ro_puf #(
    parameter NUM_PAIRS = 16,            // Generates 16 bits per challenge pass
    parameter COUNT_WINDOW = 1024        // Clock cycles per evaluation
)(
    input  wire                   clk,
    input  wire                   rst_n,

    // Control
    input  wire                   start_i,
    output reg                    done_o,

    // Generated response bits
    output reg  [NUM_PAIRS-1:0]   resp_bits_o
);

    localparam S_IDLE    = 2'd0;
    localparam S_COUNT   = 2'd1;
    localparam S_COMPARE = 2'd2;
    localparam S_DONE    = 2'd3;

    reg [1:0]  state;
    reg [15:0] window_cnt;

    // RO enable
    reg        ro_en;

    // Counters for RO frequencies
    reg [15:0] ro_cnt_a [0:NUM_PAIRS-1];
    reg [15:0] ro_cnt_b [0:NUM_PAIRS-1];

    // Ring oscillator clock outputs
    wire [NUM_PAIRS-1:0] ro_out_a;
    wire [NUM_PAIRS-1:0] ro_out_b;

    // Generate RO instances
    genvar gi;
    generate
        for (gi = 0; gi < NUM_PAIRS; gi = gi + 1) begin : gen_ro_pairs
            // RO A
            ro_cell #(
                .SEED(gi * 2 + 1)
            ) u_ro_a (
                .en_i  (ro_en),
                .clk_o (ro_out_a[gi])
            );

            // RO B
            ro_cell #(
                .SEED(gi * 2 + 2)
            ) u_ro_b (
                .en_i  (ro_en),
                .clk_o (ro_out_b[gi])
            );

            // Asynchronous pulse counters
            always @(posedge ro_out_a[gi] or negedge ro_en) begin
                if (!ro_en)
                    ro_cnt_a[gi] <= 16'd0;
                else
                    ro_cnt_a[gi] <= ro_cnt_a[gi] + 16'd1;
            end

            always @(posedge ro_out_b[gi] or negedge ro_en) begin
                if (!ro_en)
                    ro_cnt_b[gi] <= 16'd0;
                else
                    ro_cnt_b[gi] <= ro_cnt_b[gi] + 16'd1;
            end
        end
    endgenerate

    // State machine
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state       <= S_IDLE;
            window_cnt  <= 16'd0;
            ro_en       <= 1'b0;
            done_o      <= 1'b0;
            resp_bits_o <= {NUM_PAIRS{1'b0}};
        end else begin
            done_o <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (start_i) begin
                        ro_en      <= 1'b1;
                        window_cnt <= 16'd0;
                        state      <= S_COUNT;
                    end
                end

                S_COUNT: begin
                    if (window_cnt >= COUNT_WINDOW) begin
                        ro_en <= 1'b0;
                        state <= S_COMPARE;
                    end else begin
                        window_cnt <= window_cnt + 16'd1;
                    end
                end

                S_COMPARE: begin
                    for (i = 0; i < NUM_PAIRS; i = i + 1) begin
                        resp_bits_o[i] <= (ro_cnt_a[i] > ro_cnt_b[i]) ? 1'b1 : 1'b0;
                    end
                    state <= S_DONE;
                end

                S_DONE: begin
                    done_o <= 1'b1;
                    state  <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule

// ===========================================================================
//  Single Ring Oscillator Cell (3-inverter ring)
// ===========================================================================
module ro_cell #(
    parameter SEED = 1
)(
    input  wire en_i,
    output wire clk_o
);

`ifdef SYNTHESIS
    // FPGA synthesis: protect from logic optimization
    (* DONT_TOUCH = "TRUE", KEEP = "TRUE" *) wire w1, w2, w3;

    assign w1 = ~(en_i & w3);
    assign w2 = ~w1;
    assign w3 = ~w2;
    assign clk_o = w3;
`else
    // Behavioral simulation: model process variation via toggle delay
    reg ro_clk = 1'b0;

    // Delay varies slightly per instance based on SEED
    real half_period;
    initial begin
        half_period = 2.0 + (SEED % 7) * 0.15;
    end

    always begin
        if (en_i) begin
            #(half_period);
            ro_clk = ~ro_clk;
        end else begin
            ro_clk = 1'b0;
            @(posedge en_i);
        end
    end

    assign clk_o = ro_clk;
`endif

endmodule
