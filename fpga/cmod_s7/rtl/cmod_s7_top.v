// ===========================================================================
//  cmod_s7_top.v — Cmod S7 wrapper for the Flow B demo
//  SeBatt project — Hackathon Deeptech 2026
//
//  Board: Digilent Cmod S7-25 (xc7s25csga225-1), 12 MHz clock.
//  BTN0 is active-high (press = 1) and acts as a manual reset.
//  The POR counter holds reset low for ~5.5 ms after configuration/release.
//
//  Pmod JA: JA1 (J2) = SCL, JA2 (H2) = SDA.
//  UART: FPGA TX = L12, FPGA RX = K15 (FT2232 channel B).
// ===========================================================================

module cmod_s7_top (
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
        .CLK_HZ     (12_000_000),
        .BAUD       (115200),
        .BATTERY_ID (32'h42415401)
    ) u_top (
        .clk     (clk),
        .resetn  (resetn),
        .uart_rx (uart_rx),
        .uart_tx (uart_tx),
        .scl     (scl),
        .sda     (sda),
        .led     (led)
    );

endmodule
