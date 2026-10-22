// ===========================================================================
//  cmod_s7_palsu_top.v — Cmod S7 as a counterfeit battery for the demo
//  SeBatt project — Hackathon Deeptech 2026
//
//  Same SeBatt logic and the same battery ID as the KV260, but built with a
//  different key (build.tcl patches a copy of auth_ctrl.v; rtl/ stays
//  untouched). The station checks AUTH with the real key, so this board
//  answers with a wrong tag and is rejected as INVALID_HMAC.
//
//  UART sits on Pmod JA at the same positions as KV260 Pmod J2, so the
//  CP2102 lead moves from one board to the other without rewiring:
//    JA7  (H3) uart_tx -> CP2102 RXD
//    JA8  (H1) uart_rx <- CP2102 TXD
//    JA11      GND     -- CP2102 GND
//  No ADC is fitted: src_sel is tied high, so every sample is a fixed
//  3000 mV and the I2C master never starts (no ADC error on the red LED).
//
//  Board: Digilent Cmod S7-25 (xc7s25csga225-1), 12 MHz clock, BTN0 reset.
// ===========================================================================

module cmod_s7_palsu_top (
    input  wire       clk,
    input  wire       btn0,
    input  wire       uart_rx,
    output wire       uart_tx,
    inout  wire       scl,
    inout  wire       sda,
    output wire [3:0] led
);

    reg [15:0] por_cnt = 16'd0;

    always @(posedge clk) begin
        if (btn0)
            por_cnt <= 16'd0;
        else if (!(&por_cnt))
            por_cnt <= por_cnt + 16'd1;
    end

    wire resetn = &por_cnt;

    sebatt_top #(
        .CLK_HZ            (12_000_000),
        .BAUD              (115200),
        .BATTERY_ID        (32'h42415401),   // copied from the genuine battery
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
        .src_sel   (1'b1),                   // fixed 3000 mV, no ADC
        .led       (led),
        .led_green (),
        .led_red   ()
    );

endmodule
