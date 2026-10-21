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
//    4  reset button (to GND)     10  red LED
//    5, 11 GND                     6, 12 3V3
// ===========================================================================

module kv260_top #(
    parameter integer CLK_HZ = 100_000_000
) (
    input  wire uart_rx,
    output wire uart_tx,
    inout  wire scl,
    inout  wire sda,
    input  wire src_sel,
    input  wire btn,
    output wire led_green,
    output wire led_red
);

    wire clk;
    wire pl_resetn;

    design_1_wrapper u_ps (
        .pl_clk0 (clk),
        .resetn  (pl_resetn)
    );

    // Button is active-low (pulled up, press to GND); synchronise it and
    // combine with the PS reset so sebatt_top always starts cleanly.
    reg [1:0] btn_sync;

    always @(posedge clk or negedge pl_resetn) begin
        if (!pl_resetn)
            btn_sync <= 2'b00;
        else
            btn_sync <= {btn_sync[0], btn};
    end

    wire resetn = pl_resetn & btn_sync[1];

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
        .led       (),
        .led_green (led_green),
        .led_red   (led_red)
    );

endmodule
