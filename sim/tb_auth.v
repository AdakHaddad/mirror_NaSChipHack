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
    wire        locked_flag;

    auth_ctrl #(
        .CLK_HZ       (12_000_000),
        // 1 Mbaud and 12 000 cycles (1 ms) are simulation-only; hardware defaults are 115200 and 1000 ms.
        .BAUD         (1_000_000),
        .SAMPLE_CYCLES(12000)
    ) dut (
        .clk        (clk),
        .resetn     (resetn),
        .rx         (rx),
        .tx         (tx),
        .adc_start  (adc_start),
        .adc_mv     (adc_mv),
        .adc_valid  (adc_valid),
        .adc_busy   (adc_busy),
        .adc_error  (adc_error),
        .sw         (8'd0),
        .src_sel    (1'b0),
        .locked_flag(locked_flag),
        .led        (led)
    );
endmodule
