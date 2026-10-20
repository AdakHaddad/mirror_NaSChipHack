// ===========================================================================
//  sebatt_top.v — Flow B top level
//  SeBatt project — Hackathon Deeptech 2026
//
//  clk/reset + UART + ADS1115 I2C + LEDs. The ADC conversion is triggered by
//  auth_ctrl when an AUTH_REQ arrives; no software is in the sample path.
//
//  Cmod S7: CLK_HZ = 12_000_000 (12 MHz oscillator).
//  Basys 3/KV260: override CLK_HZ from the board clock.
// ===========================================================================

module sebatt_top #(
    parameter integer CLK_HZ = 12_000_000,
    parameter integer BAUD   = 115200,
    parameter [31:0]  BATTERY_ID = 32'h42415401
)(
    input  wire       clk,
    input  wire       resetn,
    input  wire       uart_rx,
    output wire       uart_tx,
    inout  wire       scl,
    inout  wire       sda,
    output wire [3:0] led
);

    wire        adc_start;
    wire [15:0] adc_mv;
    wire        adc_valid;
    wire        adc_busy;
    wire        adc_error;

    ads1115_ctrl #(
        .CLK_HZ (CLK_HZ)
    ) u_adc (
        .clk     (clk),
        .resetn  (resetn),
        .start   (adc_start),
        .mv      (adc_mv),
        .valid   (adc_valid),
        .busy    (adc_busy),
        .error   (adc_error),
        .scl     (scl),
        .sda     (sda)
    );

    auth_ctrl #(
        .CLK_HZ     (CLK_HZ),
        .BAUD       (BAUD),
        .BATTERY_ID (BATTERY_ID)
    ) u_auth (
        .clk       (clk),
        .resetn    (resetn),
        .rx        (uart_rx),
        .tx        (uart_tx),
        .adc_start (adc_start),
        .adc_mv    (adc_mv),
        .adc_valid (adc_valid),
        .adc_busy  (adc_busy),
        .adc_error (adc_error),
        .led       (led)
    );

endmodule
