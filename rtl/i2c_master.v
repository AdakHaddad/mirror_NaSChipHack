// ===========================================================================
//  i2c_master.v — I2C master for the ADS1115
//  SeBatt project — Hackathon Deeptech 2026
//
//  Transaction interface:
//    start=1 (pulse), wr_en=1:
//      START, addr+W, reg_addr, wr_data[15:8], wr_data[7:0], STOP
//    start=1 (pulse), wr_en=0:
//      START, addr+W, reg_addr, RESTART, addr+R,
//      rd_data[15:8] (master ACK), rd_data[7:0] (master NACK), STOP
//
//  SCL = 100 kHz from a 100 MHz clock (quarter-bit divider).
//  SCL/SDA are open-drain; the board needs pull-ups (the ADS1115 module has
//  them). Simulation adds weak pull-ups behind `SIMULATION.
// ===========================================================================

module i2c_master #(
    parameter integer CLK_HZ = 100_000_000,
    parameter integer I2C_HZ = 100_000
)(
    input  wire        clk,
    input  wire        resetn,
    input  wire        start,
    input  wire [6:0]  dev_addr,
    input  wire [7:0]  reg_addr,
    input  wire        wr_en,
    input  wire [15:0] wr_data,
    output reg  [15:0] rd_data,
    output reg         busy,
    output reg         done,
    output reg         ack_error,
    inout  wire        scl,
    inout  wire        sda
);

    // Quarter-bit divider: 4 phases per SCL period.
    localparam integer QUARTER = (CLK_HZ / (I2C_HZ * 4)) < 1
                                 ? 1 : (CLK_HZ / (I2C_HZ * 4));

    localparam [4:0]
        S_IDLE       = 5'd0,
        S_START      = 5'd1,
        S_ADDR_W     = 5'd2,
        S_ACK_ADDR_W = 5'd3,
        S_REG        = 5'd4,
        S_ACK_REG    = 5'd5,
        S_TX_HI      = 5'd6,
        S_ACK_TX_HI  = 5'd7,
        S_TX_LO      = 5'd8,
        S_ACK_TX_LO  = 5'd9,
        S_RSTART     = 5'd10,
        S_ADDR_R     = 5'd11,
        S_ACK_ADDR_R = 5'd12,
        S_RX_HI      = 5'd13,
        S_ACK_RX_HI  = 5'd14,
        S_RX_LO      = 5'd15,
        S_ACK_RX_LO  = 5'd16,
        S_STOP       = 5'd17;

    reg [4:0]  state;
    reg [1:0]  phase;
    reg [2:0]  bit_cnt;
    reg [7:0]  shift;
    reg [6:0]  dev_addr_r;
    reg [7:0]  reg_addr_r;
    reg        wr_en_r;
    reg [15:0] wr_data_r;
    reg [15:0] div_cnt;

    reg scl_oen;              // 1 = drive low, 0 = release (pull-up high)
    reg sda_oen;

    assign scl = scl_oen ? 1'b0 : 1'bz;
    assign sda = sda_oen ? 1'b0 : 1'bz;

    wire sda_i = sda;
    wire tick  = (div_cnt == QUARTER - 1);

`ifdef SIMULATION
    pullup (scl);
    pullup (sda);
`endif

    // -----------------------------------------------------------------------
    //  Divider
    // -----------------------------------------------------------------------
    always @(posedge clk) begin
        if (!resetn)
            div_cnt <= 16'd0;
        else if (state == S_IDLE)
            div_cnt <= 16'd0;
        else if (tick)
            div_cnt <= 16'd0;
        else
            div_cnt <= div_cnt + 1'b1;
    end

    // -----------------------------------------------------------------------
    //  Sequencer
    // -----------------------------------------------------------------------
    always @(posedge clk) begin
        if (!resetn) begin
            state      <= S_IDLE;
            phase      <= 2'd0;
            bit_cnt    <= 3'd0;
            shift      <= 8'd0;
            dev_addr_r <= 7'd0;
            reg_addr_r <= 8'd0;
            wr_en_r    <= 1'b0;
            wr_data_r  <= 16'd0;
            rd_data    <= 16'd0;
            busy       <= 1'b0;
            done       <= 1'b0;
            ack_error  <= 1'b0;
        end else begin
            done <= 1'b0;

            if (state == S_IDLE) begin
                if (start) begin
                    busy       <= 1'b1;
                    ack_error  <= 1'b0;
                    dev_addr_r <= dev_addr;
                    reg_addr_r <= reg_addr;
                    wr_en_r    <= wr_en;
                    wr_data_r  <= wr_data;
                    state      <= S_START;
                    phase      <= 2'd0;
                    bit_cnt    <= 3'd0;
                end
            end else if (tick) begin
                // Sample the slave ACK / read data while SCL is high.
                if (phase == 2'd2) begin
                    case (state)
                        S_ACK_ADDR_W,
                        S_ACK_REG,
                        S_ACK_TX_HI,
                        S_ACK_TX_LO,
                        S_ACK_ADDR_R: ack_error <= sda_i;
                        default: ;
                    endcase

                    if (state == S_RX_HI || state == S_RX_LO)
                        shift <= {shift[6:0], sda_i};
                end

                if (phase != 2'd3) begin
                    phase <= phase + 1'b1;
                end else begin
                    phase <= 2'd0;

                    case (state)
                        S_START: begin
                            shift   <= {dev_addr_r, 1'b0};
                            bit_cnt <= 3'd0;
                            state   <= S_ADDR_W;
                        end

                        S_ADDR_W: begin
                            if (bit_cnt == 3'd7) begin
                                bit_cnt <= 3'd0;
                                state   <= S_ACK_ADDR_W;
                            end else begin
                                bit_cnt <= bit_cnt + 1'b1;
                                shift   <= {shift[6:0], 1'b0};
                            end
                        end

                        S_ACK_ADDR_W: begin
                            if (ack_error) begin
                                state <= S_STOP;
                            end else begin
                                shift   <= reg_addr_r;
                                bit_cnt <= 3'd0;
                                state   <= S_REG;
                            end
                        end

                        S_REG: begin
                            if (bit_cnt == 3'd7) begin
                                bit_cnt <= 3'd0;
                                state   <= S_ACK_REG;
                            end else begin
                                bit_cnt <= bit_cnt + 1'b1;
                                shift   <= {shift[6:0], 1'b0};
                            end
                        end

                        S_ACK_REG: begin
                            if (ack_error) begin
                                state <= S_STOP;
                            end else if (wr_en_r) begin
                                shift   <= wr_data_r[15:8];
                                bit_cnt <= 3'd0;
                                state   <= S_TX_HI;
                            end else begin
                                state <= S_RSTART;
                            end
                        end

                        S_TX_HI: begin
                            if (bit_cnt == 3'd7) begin
                                bit_cnt <= 3'd0;
                                state   <= S_ACK_TX_HI;
                            end else begin
                                bit_cnt <= bit_cnt + 1'b1;
                                shift   <= {shift[6:0], 1'b0};
                            end
                        end

                        S_ACK_TX_HI: begin
                            if (ack_error) begin
                                state <= S_STOP;
                            end else begin
                                shift   <= wr_data_r[7:0];
                                bit_cnt <= 3'd0;
                                state   <= S_TX_LO;
                            end
                        end

                        S_TX_LO: begin
                            if (bit_cnt == 3'd7) begin
                                bit_cnt <= 3'd0;
                                state   <= S_ACK_TX_LO;
                            end else begin
                                bit_cnt <= bit_cnt + 1'b1;
                                shift   <= {shift[6:0], 1'b0};
                            end
                        end

                        S_ACK_TX_LO: begin
                            state <= S_STOP;
                        end

                        S_RSTART: begin
                            shift   <= {dev_addr_r, 1'b1};
                            bit_cnt <= 3'd0;
                            state   <= S_ADDR_R;
                        end

                        S_ADDR_R: begin
                            if (bit_cnt == 3'd7) begin
                                bit_cnt <= 3'd0;
                                state   <= S_ACK_ADDR_R;
                            end else begin
                                bit_cnt <= bit_cnt + 1'b1;
                                shift   <= {shift[6:0], 1'b0};
                            end
                        end

                        S_ACK_ADDR_R: begin
                            if (ack_error) begin
                                state <= S_STOP;
                            end else begin
                                shift   <= 8'd0;
                                bit_cnt <= 3'd0;
                                state   <= S_RX_HI;
                            end
                        end

                        S_RX_HI: begin
                            if (bit_cnt == 3'd7) begin
                                rd_data[15:8] <= shift;
                                bit_cnt       <= 3'd0;
                                state         <= S_ACK_RX_HI;
                            end else begin
                                bit_cnt <= bit_cnt + 1'b1;
                            end
                        end

                        S_ACK_RX_HI: begin
                            shift   <= 8'd0;
                            bit_cnt <= 3'd0;
                            state   <= S_RX_LO;
                        end

                        S_RX_LO: begin
                            if (bit_cnt == 3'd7) begin
                                rd_data[7:0] <= shift;
                                bit_cnt      <= 3'd0;
                                state        <= S_ACK_RX_LO;
                            end else begin
                                bit_cnt <= bit_cnt + 1'b1;
                            end
                        end

                        S_ACK_RX_LO: begin
                            state <= S_STOP;
                        end

                        S_STOP: begin
                            busy  <= 1'b0;
                            done  <= 1'b1;
                            state <= S_IDLE;
                        end

                        default: state <= S_IDLE;
                    endcase
                end
            end
        end
    end

    // -----------------------------------------------------------------------
    //  Open-drain output levels, by state and quarter phase
    // -----------------------------------------------------------------------
    always @(*) begin
        scl_oen = 1'b0;
        sda_oen = 1'b0;

        case (state)
            S_START: begin
                case (phase)
                    2'd0: begin scl_oen = 1'b0; sda_oen = 1'b0; end
                    2'd1: begin scl_oen = 1'b0; sda_oen = 1'b1; end
                    2'd2: begin scl_oen = 1'b1; sda_oen = 1'b1; end
                    default: begin scl_oen = 1'b1; sda_oen = 1'b1; end
                endcase
            end

            S_ADDR_W, S_ADDR_R, S_REG, S_TX_HI, S_TX_LO: begin
                case (phase)
                    2'd0: begin scl_oen = 1'b1; sda_oen = ~shift[7]; end
                    2'd1: begin scl_oen = 1'b0; sda_oen = ~shift[7]; end
                    2'd2: begin scl_oen = 1'b0; sda_oen = ~shift[7]; end
                    default: begin scl_oen = 1'b1; sda_oen = ~shift[7]; end
                endcase
            end

            S_ACK_ADDR_W, S_ACK_REG, S_ACK_TX_HI, S_ACK_TX_LO, S_ACK_ADDR_R: begin
                case (phase)
                    2'd0: begin scl_oen = 1'b1; sda_oen = 1'b0; end
                    2'd1: begin scl_oen = 1'b0; sda_oen = 1'b0; end
                    2'd2: begin scl_oen = 1'b0; sda_oen = 1'b0; end
                    default: begin scl_oen = 1'b1; sda_oen = 1'b0; end
                endcase
            end

            S_RSTART: begin
                case (phase)
                    2'd0: begin scl_oen = 1'b1; sda_oen = 1'b0; end
                    2'd1: begin scl_oen = 1'b0; sda_oen = 1'b0; end
                    2'd2: begin scl_oen = 1'b0; sda_oen = 1'b1; end
                    default: begin scl_oen = 1'b1; sda_oen = 1'b1; end
                endcase
            end

            S_RX_HI, S_RX_LO: begin
                case (phase)
                    2'd0: begin scl_oen = 1'b1; sda_oen = 1'b0; end
                    2'd1: begin scl_oen = 1'b0; sda_oen = 1'b0; end
                    2'd2: begin scl_oen = 1'b0; sda_oen = 1'b0; end
                    default: begin scl_oen = 1'b1; sda_oen = 1'b0; end
                endcase
            end

            S_ACK_RX_HI: begin
                // Master ACK: hold SDA low for the 9th clock.
                case (phase)
                    2'd0: begin scl_oen = 1'b1; sda_oen = 1'b1; end
                    2'd1: begin scl_oen = 1'b0; sda_oen = 1'b1; end
                    2'd2: begin scl_oen = 1'b0; sda_oen = 1'b1; end
                    default: begin scl_oen = 1'b1; sda_oen = 1'b1; end
                endcase
            end

            S_ACK_RX_LO: begin
                // Master NACK: release SDA for the 9th clock.
                case (phase)
                    2'd0: begin scl_oen = 1'b1; sda_oen = 1'b0; end
                    2'd1: begin scl_oen = 1'b0; sda_oen = 1'b0; end
                    2'd2: begin scl_oen = 1'b0; sda_oen = 1'b0; end
                    default: begin scl_oen = 1'b1; sda_oen = 1'b0; end
                endcase
            end

            S_STOP: begin
                case (phase)
                    2'd0: begin scl_oen = 1'b1; sda_oen = 1'b1; end
                    2'd1: begin scl_oen = 1'b0; sda_oen = 1'b1; end
                    2'd2: begin scl_oen = 1'b0; sda_oen = 1'b0; end
                    default: begin scl_oen = 1'b1; sda_oen = 1'b0; end
                endcase
            end

            default: begin
                scl_oen = 1'b0;
                sda_oen = 1'b0;
            end
        endcase
    end

endmodule
