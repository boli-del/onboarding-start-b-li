`default_nettype none

module spi_peripheral (
    input wire nCS,
    input wire clk,
    input wire rst_n,
    input wire SCLK,
    input wire COPI,
    output reg  [7:0] en_reg_out_7_0,
    output reg  [7:0] en_reg_out_15_8,
    output reg  [7:0] en_reg_pwm_7_0,
    output reg  [7:0] en_reg_pwm_15_8,
    output reg  [7:0] pwm_duty_cycle
);
reg  [15:0] message;
reg  [4:0]bit_cnt;
reg text_received = 0;
reg text_processed = 0;

wire pos_sclk = sclk_sync2 & ~sclk_sync1;
reg ncs_sync1;
reg ncs_sync2;
reg copi_sync1;
reg copi_sync2;
reg sclk_sync1;
reg sclk_sync2;


always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        //clear the text received for everything, including register
        text_received<= 0;
        text_processed <= 1'b0;
        ncs_sync1 <= 1'b1;
        ncs_sync2 <= 1'b1;
        copi_sync1 <= 1'b0;
        copi_sync2 <= 1'b0;
        sclk_sync1 <= 0;
        sclk_sync2 <= 0;
        bit_cnt  <= 5'd0;
        message  <= 16'd0;
    end
    else begin
            ncs_sync1 <= nCS;
            ncs_sync2 <= ncs_sync1;
            copi_sync1 <= COPI;
            copi_sync2 <= copi_sync1;
            sclk_sync1 <= SCLK;
            sclk_sync2 <= sclk_sync1;

                
        if (ncs_sync2 == 1'b0) begin
            if (pos_sclk && bit_cnt != 16) begin 
                //shift the message
                message <= {message[14:0], copi_sync2};
                //increment the bit count
                bit_cnt <= bit_cnt + 1;
            end
        end
        else begin 
            if (bit_cnt == 16) begin //negedge is going to be ncs_sync2 = 1, ncs_sync = 0
                //set the text received after the falling edge of the ncs which signals the end of the message
                text_received <= 1'b1;
            end else if (text_processed == 1'b1) begin
                //clear the text received since it is processed
                text_received <= 1'b0;
            end
        end
    end
end


always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin 
        //clear the text processed
        text_processed <= 1'b0;
        en_reg_out_7_0 <= 8'b0;
        en_reg_out_15_8 <= 8'b0;
        en_reg_pwm_15_8 <= 8'b0;
        en_reg_pwm_7_0 <= 8'b0;
        pwm_duty_cycle <= 8'b0;
    end else if (text_received == 1'b1 && text_processed == 1'b0) begin
        //process the text only if the text is received and not processed
        if (message[15]) begin  // Check if it's a write command
            case (message[14:8])  // Check address
                7'h00: en_reg_out_7_0 <= message[7:0];
                7'h01: en_reg_out_15_8 <= message[7:0];
                7'h02: en_reg_pwm_7_0 <= message[7:0];
                7'h03: en_reg_pwm_15_8 <= message[7:0];
                7'h04: pwm_duty_cycle <= message[7:0];
                default: ; // Handle all other addresses (5-127) by doing nothing
            endcase
        end
        text_processed <= 1'b1;
    end else if (text_processed == 1'b1) begin
        //clear the text processed after it is processed
        text_processed <= 1'b0;
    end

end

endmodule

