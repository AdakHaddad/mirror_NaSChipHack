// ===========================================================================
//  kv260_top.v — KV260 wrapper for the Flow B demo
//  SeBatt project — Hackathon Deeptech 2026
//
//  The PS block design (design_1) supplies pl_clk0 = 100 MHz and pl_resetn0;
//  the PS is used only as a clock source, all sample/auth logic stays in PL.
//
//  Pmod J2 wiring (Digilent 12-pin numbering, see RUNBOOK.md):
//    1  SCL  -> ADS1115 SCL        7  TX  -> CP2102 RXD
//    2  SDA  -> ADS1115 SDA        8  RX  <- CP2102 TXD
//    3  src_sel (0 = ADS1115)      9  green LED
//    4  heartbeat LED             10  red LED
//    5, 11 GND                     6, 12 3V3
//
//  There is no reset button: a reset restarts seq at 0 and the station then
//  reports HISTORY_ROLLBACK until seq passes its anchor. Reload the bitstream
//  (and clear the station anchor) to start over.
// ===========================================================================

module kv260_top #(
    parameter integer CLK_HZ = 100_000_000
) (
    input  wire uart_rx,
    output wire uart_tx,
    inout  wire scl,
    inout  wire sda,
    input  wire src_sel,
    output wire led_hb,
    output wire led_green,
    output wire led_red
);

    wire clk;
    wire pl_resetn;

    design_1_wrapper u_ps (
        .pl_clk0 (clk),
        .resetn  (pl_resetn)
    );

    // pl_resetn0 is asynchronous to pl_clk0: assert at once, release on a
    // clock edge so every register leaves reset in the same cycle.
    reg [1:0] rst_sync;

    always @(posedge clk or negedge pl_resetn) begin
        if (!pl_resetn)
            rst_sync <= 2'b00;
        else
            rst_sync <= {rst_sync[0], 1'b1};
    end

    wire resetn = rst_sync[1];

    wire [3:0] led;
    assign led_hb = led[0];    // ~6 Hz blink at 100 MHz: PL is alive

    sebatt_top #(
        .CLK_HZ            (CLK_HZ),
        .BAUD              (115200),
        .BATTERY_ID        (32'h42415401),
        .SAMPLE_INTERVAL_MS(1000),
        .SAMPLE_SOURCE     (2'd0)
    ) u_top (
        .clk       (clk),
        .resetn    (resetn),
        .uart_rx   (uart_rx),
        .uart_tx   (uart_tx),
        .scl       (scl),
        .sda       (sda),
        .sw        (8'd0),
        .src_sel   (src_sel),
        .led       (led),
        .led_green (led_green),
        .led_red   (led_red)
    );

endmodule
