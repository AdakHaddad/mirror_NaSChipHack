// Plain Icarus smoke test for sebatt_top: no Python/cocotb.
//
// Sends one STATUS frame over UART at 1 Mbaud and checks the 6-byte
// response [06][00][02][locked][fail_cnt][crc].
//
//   iverilog -g2012 -o smoke.vvp -s tb_smoke \
//     rtl/sha256_core.v rtl/hmac_sha256.v rtl/axil_master.v rtl/uart_if.v \
//     rtl/i2c_master.v rtl/ads1115_ctrl.v rtl/auth_ctrl.v rtl/sebatt_top.v \
//     sim/tb_smoke.v
//   vvp smoke.vvp

`timescale 1ns/1ps

module tb_smoke;
    localparam integer CLK_HZ  = 10_000_000;
    localparam integer BAUD    = 1_000_000;
    localparam integer BIT_NS  = 1000; // 1/BAUD

    reg        clk;
    reg        resetn;
    reg        rx;
    wire       tx;
    wire       scl;
    wire       sda;
    reg  [7:0] sw;
    reg        src_sel;
    wire [3:0] led;
    wire       led_green;
    wire       led_red;

    reg  [7:0] resp [0:5];
    reg  [7:0] crc;
    integer    i;

    pullup (scl);
    pullup (sda);

    sebatt_top #(
        .CLK_HZ            (CLK_HZ),
        .BAUD              (BAUD),
        .SAMPLE_INTERVAL_MS(1),
        .SAMPLE_SOURCE     (2)          // switch source: no I2C traffic
    ) dut (
        .clk       (clk),
        .resetn    (resetn),
        .uart_rx   (rx),
        .uart_tx   (tx),
        .scl       (scl),
        .sda       (sda),
        .sw        (sw),
        .src_sel   (src_sel),
        .led       (led),
        .led_green (led_green),
        .led_red   (led_red)
    );

    always #50 clk = ~clk;              // 100 ns period = 10 MHz

    function [7:0] crc8;
        input [7:0] crc_in;
        input [7:0] data;
        reg [7:0] c;
        integer k;
        begin
            c = crc_in ^ data;
            for (k = 0; k < 8; k = k + 1)
                c = c[7] ? ((c << 1) ^ 8'h31) : (c << 1);
            crc8 = c;
        end
    endfunction

    task automatic uart_send_byte;
        input [7:0] b;
        integer k;
        begin
            rx = 1'b0;
            #(BIT_NS);
            for (k = 0; k < 8; k = k + 1) begin
                rx = b[k];
                #(BIT_NS);
            end
            rx = 1'b1;
            #(BIT_NS);
        end
    endtask

    task automatic uart_recv_byte;
        output [7:0] b;
        integer k;
        begin
            @(negedge tx);
            #(BIT_NS + BIT_NS / 2);
            for (k = 0; k < 8; k = k + 1) begin
                b[k] = tx;
                #(BIT_NS);
            end
            if (tx !== 1'b1)
                $display("SMOKE FAIL: bad stop bit");
            #(BIT_NS / 2);
        end
    endtask

    initial begin
        clk     = 1'b0;
        resetn  = 1'b0;
        rx      = 1'b1;
        sw      = 8'd0;
        src_sel = 1'b0;

        #1000;
        resetn = 1'b1;
        #1000;

        // STATUS: cmd=0x06, len=0x0000, crc=0xA5
        uart_send_byte(8'h06);
        uart_send_byte(8'h00);
        uart_send_byte(8'h00);
        uart_send_byte(8'hA5);

        for (i = 0; i < 6; i = i + 1)
            uart_recv_byte(resp[i]);

        crc = 8'h00;
        for (i = 0; i < 5; i = i + 1)
            crc = crc8(crc, resp[i]);

        $display("STATUS: %02x %02x %02x %02x %02x %02x",
                 resp[0], resp[1], resp[2], resp[3], resp[4], resp[5]);
        $display("CRC: got %02x expected %02x", resp[5], crc);

        if (resp[0] == 8'h06 && resp[1] == 8'h00 && resp[2] == 8'h02 &&
            resp[3] == 8'h00 && resp[4] == 8'h00 && resp[5] == crc)
            $display("SMOKE PASS");
        else
            $display("SMOKE FAIL");

        $finish;
    end

    initial begin
        #5_000_000;
        $display("SMOKE FAIL: timeout waiting for STATUS response");
        $finish;
    end
endmodule
