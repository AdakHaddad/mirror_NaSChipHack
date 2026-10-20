// ===========================================================================
//  uart_if.v — 8N1 UART, mid-bit sampling
//  SeBatt project — Hackathon Deeptech 2026
//
//  Byte-level interface:
//    RX: rx_data + one-cycle rx_valid
//    TX: tx_data + tx_start, tx_busy while shifting, one-cycle tx_done
//
//  The bit period is CLK_HZ/BAUD clock cycles. RX samples at the middle of
//  each bit, which tolerates the small divider error on both 100 MHz and
//  12 MHz boards.
// ===========================================================================

module uart_if #(
    parameter integer CLK_HZ = 100_000_000,
    parameter integer BAUD   = 115200
)(
    input  wire       clk,
    input  wire       resetn,
    input  wire       rx,
    output wire       tx,
    output reg  [7:0] rx_data,
    output reg        rx_valid,
    input  wire [7:0] tx_data,
    input  wire       tx_start,
    output reg        tx_busy,
    output reg        tx_done
);

    localparam integer BIT_CYCLES = (CLK_HZ / BAUD) < 1 ? 1 : (CLK_HZ / BAUD);
    localparam integer HALF       = (BIT_CYCLES / 2) < 1 ? 1 : (BIT_CYCLES / 2);

    // -----------------------------------------------------------------------
    // RX synchronizer
    // -----------------------------------------------------------------------
    reg rx_meta, rx_sync, rx_prev;

    always @(posedge clk) begin
        if (!resetn) begin
            rx_meta <= 1'b1;
            rx_sync <= 1'b1;
            rx_prev <= 1'b1;
        end else begin
            rx_meta <= rx;
            rx_sync <= rx_meta;
            rx_prev <= rx_sync;
        end
    end

    wire rx_fall = rx_prev && !rx_sync;

    // -----------------------------------------------------------------------
    // RX state machine
    // -----------------------------------------------------------------------
    localparam [1:0]
        R_IDLE  = 2'd0,
        R_START = 2'd1,
        R_DATA  = 2'd2,
        R_STOP  = 2'd3;

    reg [1:0]  rstate;
    reg [15:0] rcnt;
    reg [2:0]  rbit;
    reg [7:0]  rshift;

    always @(posedge clk) begin
        if (!resetn) begin
            rstate   <= R_IDLE;
            rcnt     <= 16'd0;
            rbit     <= 3'd0;
            rshift   <= 8'd0;
            rx_data  <= 8'd0;
            rx_valid <= 1'b0;
        end else begin
            rx_valid <= 1'b0;

            case (rstate)
                R_IDLE: begin
                    rcnt <= 16'd0;
                    if (rx_fall)
                        rstate <= R_START;
                end

                R_START: begin
                    if (rcnt == HALF - 1) begin
                        rcnt <= 16'd0;
                        if (!rx_sync) begin
                            rbit   <= 3'd0;
                            rstate <= R_DATA;
                        end else begin
                            rstate <= R_IDLE;
                        end
                    end else begin
                        rcnt <= rcnt + 16'd1;
                    end
                end

                R_DATA: begin
                    if (rcnt == BIT_CYCLES - 1) begin
                        rcnt <= 16'd0;
                        rshift[rbit] <= rx_sync;
                        if (rbit == 3'd7) begin
                            rstate <= R_STOP;
                        end else begin
                            rbit <= rbit + 3'd1;
                        end
                    end else begin
                        rcnt <= rcnt + 16'd1;
                    end
                end

                R_STOP: begin
                    if (rcnt == BIT_CYCLES - 1) begin
                        rcnt <= 16'd0;
                        if (rx_sync) begin
                            rx_data  <= rshift;
                            rx_valid <= 1'b1;
                        end
                        rstate <= R_IDLE;
                    end else begin
                        rcnt <= rcnt + 16'd1;
                    end
                end

                default: rstate <= R_IDLE;
            endcase
        end
    end

    // -----------------------------------------------------------------------
    // TX state machine
    // -----------------------------------------------------------------------
    reg [9:0]  tshift;
    reg [15:0] tcnt;
    reg [3:0]  tbit;
    reg        tx_out;

    assign tx = tx_out;

    always @(posedge clk) begin
        if (!resetn) begin
            tshift  <= 10'h3FF;
            tcnt    <= 16'd0;
            tbit    <= 4'd0;
            tx_out  <= 1'b1;
            tx_busy <= 1'b0;
            tx_done <= 1'b0;
        end else begin
            tx_done <= 1'b0;

            if (tx_start && !tx_busy) begin
                tshift  <= {1'b1, tx_data, 1'b0};
                tx_out  <= 1'b0;
                tcnt    <= 16'd0;
                tbit    <= 4'd0;
                tx_busy <= 1'b1;
            end else if (tx_busy) begin
                if (tcnt == BIT_CYCLES - 1) begin
                    tcnt <= 16'd0;
                    if (tbit == 4'd9) begin
                        tx_busy <= 1'b0;
                        tx_done <= 1'b1;
                        tx_out  <= 1'b1;
                    end else begin
                        tshift <= {1'b1, tshift[9:1]};
                        tx_out <= tshift[1];
                        tbit   <= tbit + 4'd1;
                    end
                end else begin
                    tcnt <= tcnt + 16'd1;
                end
            end
        end
    end

endmodule
