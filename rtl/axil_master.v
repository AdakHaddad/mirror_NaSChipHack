// ===========================================================================
//  axil_master.v — small AXI4-Lite master for the HMAC IP
//  SeBatt project — Hackathon Deeptech 2026
//
//  One transaction per start pulse:
//    wr=1: write wdata to addr
//    wr=0: read addr into rdata
//  done is a one-cycle pulse; error captures bresp/rresp != OKAY.
// ===========================================================================

module axil_master #(
    parameter integer ADDR_WIDTH = 8,
    parameter integer DATA_WIDTH = 32
)(
    input  wire                     clk,
    input  wire                     resetn,
    input  wire                     start,
    input  wire                     wr,
    input  wire [ADDR_WIDTH-1:0]    addr,
    input  wire [DATA_WIDTH-1:0]    wdata,
    output reg  [DATA_WIDTH-1:0]    rdata,
    output reg                      busy,
    output reg                      done,
    output reg                      error,

    output reg  [ADDR_WIDTH-1:0]    m_axil_awaddr,
    output reg                      m_axil_awvalid,
    input  wire                     m_axil_awready,
    output reg  [DATA_WIDTH-1:0]    m_axil_wdata,
    output reg  [DATA_WIDTH/8-1:0]  m_axil_wstrb,
    output reg                      m_axil_wvalid,
    input  wire                     m_axil_wready,
    input  wire [1:0]               m_axil_bresp,
    input  wire                     m_axil_bvalid,
    output reg                      m_axil_bready,
    output reg  [ADDR_WIDTH-1:0]    m_axil_araddr,
    output reg                      m_axil_arvalid,
    input  wire                     m_axil_arready,
    input  wire [DATA_WIDTH-1:0]    m_axil_rdata,
    input  wire [1:0]               m_axil_rresp,
    input  wire                     m_axil_rvalid,
    output reg                      m_axil_rready
);

    localparam [2:0]
        A_IDLE  = 3'd0,
        A_WRITE = 3'd1,
        A_WB    = 3'd2,
        A_AR    = 3'd3,
        A_R     = 3'd4;

    reg [2:0] astate;

    always @(posedge clk) begin
        if (!resetn) begin
            astate          <= A_IDLE;
            busy            <= 1'b0;
            done            <= 1'b0;
            error           <= 1'b0;
            rdata           <= {DATA_WIDTH{1'b0}};
            m_axil_awaddr   <= {ADDR_WIDTH{1'b0}};
            m_axil_awvalid  <= 1'b0;
            m_axil_wdata    <= {DATA_WIDTH{1'b0}};
            m_axil_wstrb    <= {(DATA_WIDTH/8){1'b1}};
            m_axil_wvalid   <= 1'b0;
            m_axil_bready   <= 1'b0;
            m_axil_araddr   <= {ADDR_WIDTH{1'b0}};
            m_axil_arvalid  <= 1'b0;
            m_axil_rready   <= 1'b0;
        end else begin
            done <= 1'b0;

            case (astate)
                A_IDLE: begin
                    if (start && !busy) begin
                        busy  <= 1'b1;
                        error <= 1'b0;
                        if (wr) begin
                            m_axil_awaddr  <= addr;
                            m_axil_awvalid <= 1'b1;
                            m_axil_wdata   <= wdata;
                            m_axil_wstrb   <= {(DATA_WIDTH/8){1'b1}};
                            m_axil_wvalid  <= 1'b1;
                            astate         <= A_WRITE;
                        end else begin
                            m_axil_araddr  <= addr;
                            m_axil_arvalid <= 1'b1;
                            astate         <= A_AR;
                        end
                    end
                end

                A_WRITE: begin
                    if (m_axil_awready && m_axil_wready) begin
                        m_axil_awvalid <= 1'b0;
                        m_axil_wvalid  <= 1'b0;
                        m_axil_bready  <= 1'b1;
                        astate         <= A_WB;
                    end
                end

                A_WB: begin
                    if (m_axil_bvalid) begin
                        m_axil_bready <= 1'b0;
                        if (m_axil_bresp != 2'b00)
                            error <= 1'b1;
                        done   <= 1'b1;
                        busy   <= 1'b0;
                        astate <= A_IDLE;
                    end
                end

                A_AR: begin
                    if (m_axil_arready) begin
                        m_axil_arvalid <= 1'b0;
                        m_axil_rready  <= 1'b1;
                        astate         <= A_R;
                    end
                end

                A_R: begin
                    if (m_axil_rvalid) begin
                        rdata         <= m_axil_rdata;
                        m_axil_rready <= 1'b0;
                        if (m_axil_rresp != 2'b00)
                            error <= 1'b1;
                        done   <= 1'b1;
                        busy   <= 1'b0;
                        astate <= A_IDLE;
                    end
                end

                default: astate <= A_IDLE;
            endcase
        end
    end

endmodule
