`default_nettype none

module spi_peripheral (
    input wire ncs;
    input wire clk;
    input wire rst_n;
    input wire sclk;
    input wire copi;
    output reg  [7:0] en_reg_out_7_0;
    output reg  [7:0] en_reg_out_15_8;
    output reg  [7:0] en_reg_pwm_7_0;
    output reg  [7:0] en_reg_pwm_15_8;
    output reg  [7:0] pwm_duty_cycle;
    output reg message;
    output reg bit_cnt;
    output reg text_received = 0;
    output reg text_processed = 0;
    reg ncs_sync1, ncs_sync2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            //clear the text received
            text_received<= 0;
            ncs_sync1 <= 1'b1;
            ncs_sync2 <= 1'b1;
        end
        else begin
            ncs_sync1 <= ncs;
            ncs_sync2 <= ncs_sync1;
        end
        else if (ncs_sync2 == 1'b0) begin
            if (posedge sclk) begin
                //shift the message
                message <= {message[14:0], copi}
                //increment the bit count
                bit_cnt <= bit_cnt + 1;
            end
        end
        and else begin 
            if (ncs_sync2 == 1'b1) begin
                //set the text received after the falling edge of the ncs which signals the end of the message
                text_received <= 1'b1;
            end else if (text_processed == 1'b1) begin
                //clear the text received since it is processed
                text_received <= 1'b0;
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin 
            //clear the text processed
            text_processed <= 1'b0;
        
        end else if (text_received == 1'b1 && text_processed == 1'b0) begin
            //process the text only if the text is received and not processed
            text_processed <= 1'b1;
        end else if (text_processed == 1'b1) begin
            //clear the text processed after it is processed
            text_processed <= 1'b0;
        end
    end
);
endmodule

