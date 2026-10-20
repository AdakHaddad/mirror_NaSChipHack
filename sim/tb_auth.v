// Simulation wrapper: use the Cmod S7 clock so the UART test is fast enough.
module tb_auth;
    reg         clk;
    reg         resetn;
    reg         rx;
    wire        tx;

    wire        adc_start;
    reg  [15:0] adc_mv;
    reg         adc_valid;
    reg         adc_busy;
    reg         adc_error;

    wire [3:0]  led;

    auth_ctrl #(
        .CLK_HZ (12_000_000),
        .BAUD   (115200)
    ) dut (
        .clk       (clk),
        .resetn    (resetn),
        .rx        (rx),
        .tx        (tx),
        .adc_start (adc_start),
        .adc_mv    (adc_mv),
        .adc_valid (adc_valid),
        .adc_busy  (adc_busy),
        .adc_error (adc_error),
        .led       (led)
    );
endmodule
