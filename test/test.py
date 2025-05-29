# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, with_timeout
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray
from cocotb.result import SimTimeoutError

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    # Write your test here
    dut._log.info("Start Frequency test")
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    dut._log.info("Reset")
    dut.rst_n.value = 0
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 5) #waiting for stable state
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5) #waiting for stable state
    time_out = 100000 #for handling timeout errors
    time_cyclec_count = 0
    #50% duty cycle
    dut._log.info("Testing at 50 percent duty cycle")
    dut._log.info("Write transaction, address 0x00, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0x01)  # Write transaction
    await send_spi_transaction(dut, 1, 0x02, 0x01)  # Enable PWM for output 0
    await send_spi_transaction(dut, 1, 0x04, 0x80)  #set 50% duty cycle
    await ClockCycles(dut.clk, 10000) #waiting for stable state
    rising_edges = []
    falling_edges = []
    await with_timeout(RisingEdge(dut.uio_out), 10000, 'us')
    rising_edges.append(cocotb.utils.get_sim_time(units="ns"))
    await with_timeout(FallingEdge(dut.uio_out), 10000, 'us')
    falling_edges.append(cocotb.utils.get_sim_time(units="ns"))
    await with_timeout(RisingEdge(dut.uio_out), 10000, 'us')
    rising_edges.append(cocotb.utils.get_sim_time(units="ns"))

    period = rising_edges[1] - rising_edges[0]
    frequency = 1 / period
    dut._log.info(f"Period: {period} ns, Frequency: {frequency} Hz")
    assert frequency <= 3030 and frequency >= 2970, f"Expected frequency to be 3000 Hz, got {frequency} Hz"

    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    dut._log.info("Start PWM Duty Cycle test")
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    dut._log.info("Reset")
    dut.rst_n.value = 0
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 5) #waiting for stable state
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5) #waiting for stable state

    #50% duty cycle
    dut._log.info("Testing 50% duty cycle")
    dut._log.info("Write transaction, address 0x00, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0x01)  # Write transaction
    await send_spi_transaction(dut, 1, 0x02, 0x01)  # Enable PWM for output 0
    await send_spi_transaction(dut, 1, 0x04, 0x80)  #set 50% duty cycle
    await ClockCycles(dut.clk, 10000) #waiting for stable state
    rising_edges = []
    falling_edges = []
    time_out = 100000 #for handling timeout errors
    time_cyclec_count = 0

    #detect rising and falling edges
    while dut.uio_out.value == 0: 
        await ClockCycles(dut.clk, 1)
        time_cyclec_count += 1
        if time_cyclec_count > time_out:
            raise TimeoutError("Time out waiting for rising edge")
    time_cyclec_count = 0
    rising_edges.append(cocotb.utils.get_sim_time(units="ns"))
    while dut.uio_out.value == 1:
        await ClockCycles(dut.clk, 1)
        time_cyclec_count += 1
        if time_cyclec_count > time_out:
            raise TimeoutError("Time out waiting for falling edge")
    time_cyclec_count = 0
    falling_edges.append(cocotb.utils.get_sim_time(units="ns"))
    while dut.uio_out.value == 0:
        await ClockCycles(dut.clk, 1)
        time_cyclec_count += 1
        if time_cyclec_count > time_out:
            raise TimeoutError("Time out waiting for rising edge")
    time_cyclec_count = 0
    rising_edges.append(cocotb.utils.get_sim_time(units="ns"))
    
    #calculate period, hightimes, and frequency
    period = rising_edges[1] - rising_edges[0]
    high_time = falling_edges[0]-rising_edges[0]
    duty_cycle = (high_time/period)*100
    dut._log.info(f"Period: {period} ns, High time: {high_time} ns, Duty Cycle: {duty_cycle}%")
    assert high_time <= 55 and high_time >= 45, f"Expected duty cycle to be 50 %, got {high_time} %"
    dut._log.info("50 percent duty cycle passed successfully")

    #handling edge_case of 0 percent
    dut._log.info("Testing 0 percent duty cycle")
    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 10000)
    assert dut.uio_out.value == 0, f"Expected 0% duty cycle, got {dut.uio_out[0].value}"
    dut._log.info("0 percent duty cycle passed successfully")

    #handling edge_case of 100 percent
    dut._log.info("Testing 100 percent duty cycle")
    dut._log.info("Write transaction, address 0x00, data 0x02")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 1000)
    assert dut.uio_out.value == 1, f"Expected 100% duty cycle, got {dut.uio_out[0].value}"
    dut._log.info("100 percent duty cycle passed successfully")

    dut._log.info("PWM Duty Cycle test completed successfully")
