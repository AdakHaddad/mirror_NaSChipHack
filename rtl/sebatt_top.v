// ===========================================================================
//  sebatt_top.v — Flow B top level
//  SeBatt project — Hackathon Deeptech 2026
//
//  clk/reset + UART + ADS1115 I2C + LEDs. auth_ctrl samples every
//  SAMPLE_INTERVAL_MS, signs each sample (0x53 prefix), and answers
//  AUTH_REQ (0x41) and READ_HIST_REQ (0x48 summary) on the UART; no
//  software is in the sample path.
//
//  Sources (spec section 3): the sample comes from ADS1115 by default.
//  src_sel sets the switch source (3000 + sw*5) at board level; ROM_MV is
//  a constant placeholder until the ROM record playback exists (source 1).
//
//  Cmod S7: CLK_HZ = 12_000_000 (12 MHz oscillator).
//  Basys 3/KV260: override CLK_HZ from the board clock.
// ===========================================================================

module sebatt_top #(
    parameter integer CLK_HZ = 12_000_000,
    parameter integer BAUD   = 115200,
    parameter [31:0]  BATTERY_ID = 32'h42415401,
    parameter integer SAMPLE_INTERVAL_MS = 1000,
    parameter [15:0]  ROM_MV = 16'd0,
    parameter [1:0]   SAMPLE_SOURCE = 2'd0
)(
    input  wire       clk,
    input  wire       resetn,
    input  wire       uart_rx,
    output wire       uart_tx,
    inout  wire       scl,
    inout  wire       sda,
    input  wire [7:0] sw,
    input  wire       src_sel,
    output wire [3:0] led,
    output wire       led_green,
    output wire       led_red
);

    wire        adc_start;
    wire [15:0] adc_mv;
    wire        adc_valid;
    wire        adc_busy;
    wire        adc_error;
    wire        chip_locked;

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
        .CLK_HZ            (CLK_HZ),
        .BAUD              (BAUD),
        .BATTERY_ID        (BATTERY_ID),
        .SAMPLE_INTERVAL_MS(SAMPLE_INTERVAL_MS),
        .ROM_MV            (ROM_MV),
        .SAMPLE_SOURCE     (SAMPLE_SOURCE)
    ) u_auth (
        .clk        (clk),
        .resetn     (resetn),
        .rx         (uart_rx),
        .tx         (uart_tx),
        .adc_start  (adc_start),
        .adc_mv     (adc_mv),
        .adc_valid  (adc_valid),
        .adc_busy   (adc_busy),
        .adc_error  (adc_error),
        .sw         (sw),
        .src_sel    (src_sel),
        .locked_flag(chip_locked),
        .led        (led)
    );

    // Green/red pair for the KV260 Pmod (pins 9/10, spec section 13): green
    // lights up after the last accepted command, red shows lock or error.
    assign led_green = led[2] & ~led[3];
    assign led_red   = led[3];

endmodule
