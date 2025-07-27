#!/usr/bin/env python3
"""
MCF54415 ColdFire BDM (Background Debug Mode) Interface
Basic implementation for Raspberry Pi 2

BDM Protocol Overview:
- DSI: Data Serial Input (Pi -> MCU)
- DSO: Data Serial Output (MCU -> Pi) 
- DSCLK: Data Serial Clock (Pi -> MCU)
- BKPT: Breakpoint signal
- RESET: Reset signal
"""

import RPi.GPIO as GPIO
import time
import sys
import os

class MCF54415_BDM:
    def __init__(self, dsi_pin=13, dso_pin=6, dsclk_pin=19, bkpt_pin=26, reset_pin=17):
        """Initialize BDM interface pins"""
        self.DSI_PIN = dsi_pin      # Data Serial Input
        self.DSO_PIN = dso_pin      # Data Serial Output  
        self.DSCLK_PIN = dsclk_pin  # Data Serial Clock
        self.BKPT_PIN = bkpt_pin    # Breakpoint
        self.RESET_PIN = reset_pin  # Reset
        
        # BDM timing parameters (microseconds)
        self.CLOCK_DELAY = 1        # 1MHz BDM clock
        self.SETUP_TIME = 0.5       # Data setup time
        
        self.setup_gpio()
        
    def setup_gpio(self):
        """Configure GPIO pins"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Output pins
        GPIO.setup(self.DSI_PIN, GPIO.OUT)
        GPIO.setup(self.DSCLK_PIN, GPIO.OUT) 
        GPIO.setup(self.BKPT_PIN, GPIO.OUT)
        GPIO.setup(self.RESET_PIN, GPIO.OUT)
        
        # Input pin
        GPIO.setup(self.DSO_PIN, GPIO.IN)
        
        # Initialize to safe states
        GPIO.output(self.DSI_PIN, 0)
        GPIO.output(self.DSCLK_PIN, 0)
        GPIO.output(self.BKPT_PIN, 1)    # Active low
        GPIO.output(self.RESET_PIN, 1)   # Active low
        
    def cleanup(self):
        """Clean up GPIO resources"""
        GPIO.cleanup()
        
    def clock_pulse(self):
        """Generate a single BDM clock pulse"""
        time.sleep(self.SETUP_TIME / 1000000)
        GPIO.output(self.DSCLK_PIN, 1)
        time.sleep(self.CLOCK_DELAY / 1000000)
        GPIO.output(self.DSCLK_PIN, 0)
        time.sleep(self.CLOCK_DELAY / 1000000)
        
    def write_bit(self, bit):
        """Write a single bit to BDM interface"""
        GPIO.output(self.DSI_PIN, 1 if bit else 0)
        self.clock_pulse()
        
    def read_bit(self):
        """Read a single bit from BDM interface"""
        self.clock_pulse()
        return GPIO.input(self.DSO_PIN)
        
    def bdm_sync(self):
        """Perform BDM synchronization sequence"""
        print("Performing BDM sync...")
        
        # Send 16 clock pulses with DSI low
        GPIO.output(self.DSI_PIN, 0)
        for i in range(16):
            self.clock_pulse()
            
        # Wait for DSO to go high (sync achieved)
        timeout = 1000  # 1000 attempts
        sync_attempts = 0
        while timeout > 0:
            dso_state = GPIO.input(self.DSO_PIN)
            print(f"Debug: DSO state = {dso_state}, attempt {sync_attempts}")
            if dso_state == 1:
                print("BDM sync successful!")
                return True
            self.clock_pulse()
            timeout -= 1
            sync_attempts += 1
            
        print("BDM sync failed!")
        return False
        
    def reset_target(self):
        """Reset the target MCU"""
        print("Resetting target...")
        GPIO.output(self.RESET_PIN, 0)  # Assert reset
        time.sleep(0.1)                 # Hold for 100ms
        GPIO.output(self.RESET_PIN, 1)  # Release reset
        time.sleep(0.1)                 # Wait for startup
        
    def enter_debug_mode(self):
        """Force target into debug mode via BKPT"""
        print("Entering debug mode...")
        GPIO.output(self.BKPT_PIN, 0)   # Assert breakpoint
        time.sleep(0.001)               # Hold for 1ms
        GPIO.output(self.BKPT_PIN, 1)   # Release breakpoint
        
    def write_command(self, command, data_bits=0):
        """Write a BDM command (16 bits) optionally followed by data"""
        # Send command (16 bits, MSB first)
        for i in range(15, -1, -1):
            bit = (command >> i) & 1
            self.write_bit(bit)
            
        # Send data if provided
        if data_bits > 0:
            for i in range(data_bits - 1, -1, -1):
                bit = (data >> i) & 1
                self.write_bit(bit)
                
    def read_response(self, num_bits):
        """Read BDM response (specified number of bits)"""
        result = 0
        for i in range(num_bits):
            bit = self.read_bit()
            result = (result << 1) | bit
        return result
        
    def read_memory_32(self, address):
        """Read 32-bit word from memory"""
        # ColdFire BDM command for 32-bit memory read
        # Command format: 0x2180 + size bits
        cmd = 0x2190  # Read longword command
        
        self.write_command(cmd)
        
        # Send 32-bit address
        for i in range(31, -1, -1):
            bit = (address >> i) & 1
            self.write_bit(bit)
            
        # Read 32-bit data response
        data = self.read_response(32)
        return data
        
    def write_memory_32(self, address, data):
        """Write 32-bit word to memory"""
        # ColdFire BDM command for 32-bit memory write
        cmd = 0x2080  # Write longword command
        
        self.write_command(cmd)
        
        # Send 32-bit address
        for i in range(31, -1, -1):
            bit = (address >> i) & 1
            self.write_bit(bit)
            
        # Send 32-bit data
        for i in range(31, -1, -1):
            bit = (data >> i) & 1
            self.write_bit(bit)
            
    def read_register(self, reg_num):
        """Read CPU register (A0-A7, D0-D7)"""
        # Command for reading registers
        if reg_num < 8:  # Data registers D0-D7
            cmd = 0x2580 | reg_num
        else:  # Address registers A0-A7
            cmd = 0x2588 | (reg_num - 8)
            
        print(f"Debug: Sending register read command 0x{cmd:04X} for reg {reg_num}")
        self.write_command(cmd)
        result = self.read_response(32)
        print(f"Debug: Got response 0x{result:08X}")
        return result
        
    def write_register(self, reg_num, data):
        """Write CPU register (A0-A7, D0-D7)"""
        # Command for writing registers
        if reg_num < 8:  # Data registers D0-D7
            cmd = 0x2480 | reg_num
        else:  # Address registers A0-A7
            cmd = 0x2488 | (reg_num - 8)
            
        self.write_command(cmd)
        
        # Send 32-bit data
        for i in range(31, -1, -1):
            bit = (data >> i) & 1
            self.write_bit(bit)

def print_help():
    """Print available commands"""
    help_text = """
Available Commands:
==================
init         - Initialize BDM connection (reset + sync)
sync         - Perform BDM synchronization
reset        - Reset target MCU
debug        - Enter debug mode
test         - Test BDM hardware connectivity
status       - Show connection and GPIO status

Memory Commands:
rm <addr>    - Read 32-bit memory at address (hex)
wm <addr> <data> - Write 32-bit data to memory address (hex)
dump <addr> <count> - Dump memory starting at address (hex)
dumpfile <start> <end> <file> [format] - Dump memory region to file
map          - Show MCF54415 memory map
quickdump <region> - Quick dump of common regions

Register Commands:
rr <reg>     - Read register (d0-d7, a0-a7)
wr <reg> <data> - Write register with data (hex)
regs         - Display all registers

Utility Commands:
help         - Show this help message
quit/exit    - Exit program

Troubleshooting Commands:
test         - Test hardware connections and GPIO
status       - Check connection status and pin states

Examples:
test              - Check if BDM hardware is connected
status            - See current GPIO pin states
rm 0x1000         - Read memory at 0x1000
wm 0x1000 0x12345678 - Write 0x12345678 to address 0x1000
rr d0             - Read data register D0
wr a7 0xFF000000  - Write 0xFF000000 to address register A7
dump 0x0 16       - Dump 16 words starting at address 0x0

OS Dumping Examples:
map               - Show memory regions where OS might be located
quickdump bootrom - Quick dump of boot ROM region
quickdump flash   - Quick dump of external flash (main OS)
quickdump all     - Dump all common regions
dumpfile 0x40000000 0x40100000 os.bin - Dump 1MB from flash to file
dumpfile 0x0 0x100000 bootrom.bin hex - Dump boot ROM in hex format
dumpfile 0x40000000 0x41000000 flash.srec srec - Dump 16MB flash as S-record
"""
    print(help_text)

def parse_register(reg_str):
    """Parse register string (d0-d7, a0-a7) to register number"""
    reg_str = reg_str.lower()
    if reg_str.startswith('d') and len(reg_str) == 2:
        reg_num = int(reg_str[1])
        if 0 <= reg_num <= 7:
            return reg_num
    elif reg_str.startswith('a') and len(reg_str) == 2:
        reg_num = int(reg_str[1])
        if 0 <= reg_num <= 7:
            return reg_num + 8
    raise ValueError(f"Invalid register: {reg_str}")

def parse_hex_value(hex_str):
    """Parse hexadecimal string to integer"""
    hex_str = hex_str.strip()
    if hex_str.startswith('0x') or hex_str.startswith('0X'):
        return int(hex_str, 16)
    else:
        return int(hex_str, 16)

def bdm_console():
    """Interactive BDM console"""
    bdm = MCF54415_BDM()
    connected = False
    
    print("MCF54415 BDM Console")
    print("Type 'help' for available commands")
    print("=" * 40)
    
    try:
        while True:
            try:
                command = input("BDM> ").strip().lower()
                
                if not command:
                    continue
                    
                parts = command.split()
                cmd = parts[0]
                
                if cmd in ['quit', 'exit']:
                    break
                    
                elif cmd == 'help':
                    print_help()
                    
                elif cmd == 'init':
                    print("Initializing BDM connection...")
                    bdm.reset_target()
                    bdm.enter_debug_mode()
                    if bdm.bdm_sync():
                        connected = True
                        print("BDM connection established!")
                    else:
                        connected = False
                        print("Failed to establish BDM connection!")
                        
                elif cmd == 'sync':
                    if bdm.bdm_sync():
                        connected = True
                        print("BDM sync successful!")
                    else:
                        connected = False
                        print("BDM sync failed!")
                        
                elif cmd == 'reset':
                    bdm.reset_target()
                    connected = False
                    print("Target reset!")
                    
                elif cmd == 'test':
                    print("Testing BDM connectivity...")
                    print(f"DSI pin (output): GPIO {bdm.DSI_PIN}")
                    print(f"DSO pin (input):  GPIO {bdm.DSO_PIN}")
                    print(f"DSCLK pin (output): GPIO {bdm.DSCLK_PIN}")
                    print(f"BKPT pin (output): GPIO {bdm.BKPT_PIN}")
                    print(f"RESET pin (output): GPIO {bdm.RESET_PIN}")
                    print()
                    
                    # Test GPIO states
                    print("Current GPIO states:")
                    print(f"DSO (should vary): {GPIO.input(bdm.DSO_PIN)}")
                    
                    # Test clock generation
                    print("Testing clock generation...")
                    for i in range(5):
                        GPIO.output(bdm.DSCLK_PIN, 1)
                        time.sleep(0.001)
                        GPIO.output(bdm.DSCLK_PIN, 0) 
                        time.sleep(0.001)
                        print(f"Clock pulse {i+1}, DSO = {GPIO.input(bdm.DSO_PIN)}")
                    
                elif cmd == 'status':
                    if not connected:
                        print("Status: Not connected")
                    else:
                        print("Status: Connected")
                        
                    print(f"Current GPIO states:")
                    print(f"  DSI:   {GPIO.input(bdm.DSI_PIN)}")
                    print(f"  DSO:   {GPIO.input(bdm.DSO_PIN)}")  
                    print(f"  DSCLK: {GPIO.input(bdm.DSCLK_PIN)}")
                    print(f"  BKPT:  {GPIO.input(bdm.BKPT_PIN)}")
                    print(f"  RESET: {GPIO.input(bdm.RESET_PIN)}")
                    
                elif cmd == 'debug':
                    bdm.enter_debug_mode()
                    print("Entered debug mode!")
                    print("Tip: Try 'status' to check GPIO states")
                    
                elif cmd == 'rm':
                    if not connected:
                        print("Error: Not connected! Use 'init' first.")
                        continue
                    if len(parts) != 2:
                        print("Usage: rm <address>")
                        continue
                    try:
                        addr = parse_hex_value(parts[1])
                        data = bdm.read_memory_32(addr)
                        print(f"Memory[0x{addr:08X}] = 0x{data:08X}")
                    except ValueError as e:
                        print(f"Error: {e}")
                    except Exception as e:
                        print(f"BDM Error: {e}")
                        
                elif cmd == 'wm':
                    if not connected:
                        print("Error: Not connected! Use 'init' first.")
                        continue
                    if len(parts) != 3:
                        print("Usage: wm <address> <data>")
                        continue
                    try:
                        addr = parse_hex_value(parts[1])
                        data = parse_hex_value(parts[2])
                        bdm.write_memory_32(addr, data)
                        print(f"Memory[0x{addr:08X}] = 0x{data:08X}")
                    except ValueError as e:
                        print(f"Error: {e}")
                    except Exception as e:
                        print(f"BDM Error: {e}")
                        
                elif cmd == 'dump':
                    if not connected:
                        print("Error: Not connected! Use 'init' first.")
                        continue
                    if len(parts) not in [2, 3]:
                        print("Usage: dump <address> [count]")
                        continue
                    try:
                        addr = parse_hex_value(parts[1])
                        count = int(parts[2]) if len(parts) == 3 else 8
                        
                        print(f"Memory dump starting at 0x{addr:08X}:")
                        for i in range(count):
                            current_addr = addr + (i * 4)
                            data = bdm.read_memory_32(current_addr)
                            print(f"0x{current_addr:08X}: 0x{data:08X}")
                    except ValueError as e:
                        print(f"Error: {e}")
                    except Exception as e:
                        print(f"BDM Error: {e}")
                        
                elif cmd == 'dumpfile':
                    if not connected:
                        print("Error: Not connected! Use 'init' first.")
                        continue
                    if len(parts) not in [4, 5]:
                        print("Usage: dumpfile <start_addr> <end_addr> <filename> [format]")
                        print("Formats: bin (default), hex, srec")
                        continue
                    try:
                        start_addr = parse_hex_value(parts[1])
                        end_addr = parse_hex_value(parts[2])
                        filename = parts[3]
                        format_type = parts[4].lower() if len(parts) == 5 else 'bin'
                        
                        # Ensure filename is in current directory
                        filename = os.path.basename(filename)  # Remove any path components
                        full_path = os.path.join(os.getcwd(), filename)
                        
                        if start_addr >= end_addr:
                            print("Error: Start address must be less than end address")
                            continue
                            
                        size = end_addr - start_addr
                        word_count = (size + 3) // 4  # Round up to nearest word
                        
                        print(f"Dumping 0x{size:X} bytes from 0x{start_addr:08X} to 0x{end_addr:08X}")
                        print(f"Output file: {full_path}")
                        print("Reading memory... (this may take a while)")
                        
                        # Read memory in chunks with progress indicator
                        chunk_size = 1024  # Read 1KB at a time
                        data = bytearray()
                        
                        for offset in range(0, word_count, chunk_size // 4):
                            current_addr = start_addr + (offset * 4)
                            remaining_words = min(chunk_size // 4, word_count - offset)
                            
                            # Progress indicator
                            progress = (offset * 4 * 100) // size
                            print(f"\rProgress: {progress}% (0x{current_addr:08X})", end='', flush=True)
                            
                            for i in range(remaining_words):
                                word_addr = current_addr + (i * 4)
                                if word_addr >= end_addr:
                                    break
                                    
                                try:
                                    word_data = bdm.read_memory_32(word_addr)
                                    # Convert to bytes (big-endian)
                                    data.extend(word_data.to_bytes(4, 'big'))
                                except Exception as e:
                                    print(f"\nError reading at 0x{word_addr:08X}: {e}")
                                    # Fill with zeros for inaccessible memory
                                    data.extend(b'\x00\x00\x00\x00')
                        
                        print(f"\rProgress: 100% - Writing to file...")
                        
                        # Trim data to exact size requested
                        data = data[:size]
                        
                        # Write file in requested format
                        if format_type == 'bin':
                            with open(full_path, 'wb') as f:
                                f.write(data)
                        elif format_type == 'hex':
                            with open(full_path, 'w') as f:
                                for i in range(0, len(data), 16):
                                    addr = start_addr + i
                                    chunk = data[i:i+16]
                                    hex_bytes = ' '.join(f'{b:02X}' for b in chunk)
                                    ascii_chars = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
                                    f.write(f"{addr:08X}: {hex_bytes:<48} |{ascii_chars}|\n")
                        elif format_type == 'srec':
                            with open(full_path, 'w') as f:
                                # S0 record (header)
                                f.write("S00F000068656C6C6F202020202000003C\n")
                                
                                # S3 records (32-bit address data)
                                for i in range(0, len(data), 32):
                                    addr = start_addr + i
                                    chunk = data[i:i+32]
                                    
                                    # Build S3 record
                                    record_len = len(chunk) + 5  # data + addr + checksum
                                    record = f"S3{record_len:02X}{addr:08X}"
                                    record += chunk.hex().upper()
                                    
                                    # Calculate checksum
                                    checksum = record_len + ((addr >> 24) & 0xFF) + ((addr >> 16) & 0xFF) + ((addr >> 8) & 0xFF) + (addr & 0xFF)
                                    for b in chunk:
                                        checksum += b
                                    checksum = (~checksum) & 0xFF
                                    
                                    record += f"{checksum:02X}\n"
                                    f.write(record)
                                
                                # S7 record (termination)
                                f.write(f"S705{start_addr:08X}")
                                term_checksum = 5 + ((start_addr >> 24) & 0xFF) + ((start_addr >> 16) & 0xFF) + ((start_addr >> 8) & 0xFF) + (start_addr & 0xFF)
                                term_checksum = (~term_checksum) & 0xFF
                                f.write(f"{term_checksum:02X}\n")
                        else:
                            print(f"Error: Unknown format '{format_type}'")
                            continue
                            
                        print(f"Successfully dumped {len(data)} bytes to {filename}")
                        
                    except ValueError as e:
                        print(f"Error: {e}")
                    except Exception as e:
                        print(f"Error: {e}")
                        
                elif cmd == 'map':
                    print("MCF54415 Memory Map:")
                    print("=" * 50)
                    print("0x00000000 - 0x000FFFFF : Boot ROM (1MB)")
                    print("0x00100000 - 0x001FFFFF : Reserved")
                    print("0x20000000 - 0x2001FFFF : Internal SRAM (128KB)")
                    print("0x40000000 - 0x400FFFFF : FlexBus CS0 (External Flash)")
                    print("0x60000000 - 0x600FFFFF : FlexBus CS1")
                    print("0x80000000 - 0x800FFFFF : FlexBus CS2") 
                    print("0xA0000000 - 0xA00FFFFF : FlexBus CS3")
                    print("0xFC000000 - 0xFFFFFFFF : Internal Peripherals")
                    print("")
                    print("Common OS locations:")
                    print("- Boot ROM: 0x00000000 (reset vectors, boot code)")
                    print("- External Flash: 0x40000000 (main OS image)")
                    print("- Internal RAM: 0x20000000 (runtime data)")
                    
                elif cmd == 'quickdump':
                    if not connected:
                        print("Error: Not connected! Use 'init' first.")
                        continue
                    if len(parts) != 2:
                        print("Usage: quickdump <region>")
                        print("Regions: bootrom, flash, sram, all")
                        continue
                        
                    region = parts[1].lower()
                    
                    if region == 'bootrom':
                        start, end = 0x00000000, 0x00100000
                        filename = "mcf54415_bootrom.bin"
                    elif region == 'flash':
                        start, end = 0x40000000, 0x40100000  # 1MB
                        filename = "mcf54415_flash.bin"
                    elif region == 'sram':
                        start, end = 0x20000000, 0x20020000
                        filename = "mcf54415_sram.bin"
                    elif region == 'all':
                        print("Dumping all regions to current directory...")
                        print("This will create: mcf54415_bootrom.bin, mcf54415_flash.bin, mcf54415_sram.bin")
                        confirm = input("This will take a long time. Continue? (y/N): ").lower()
                        if confirm != 'y':
                            print("Cancelled.")
                            continue
                            
                        regions = [
                            (0x00000000, 0x00100000, "mcf54415_bootrom.bin"),
                            (0x40000000, 0x40100000, "mcf54415_flash.bin"), 
                            (0x20000000, 0x20020000, "mcf54415_sram.bin")
                        ]
                        
                        for i, (start_addr, end_addr, fname) in enumerate(regions, 1):
                            print(f"\n[{i}/3] Dumping {fname}...")
                            full_path = os.path.join(os.getcwd(), fname)
                            
                            size = end_addr - start_addr
                            word_count = (size + 3) // 4
                            chunk_size = 1024
                            data = bytearray()
                            
                            print(f"Range: 0x{start_addr:08X} - 0x{end_addr:08X} ({size // 1024}KB)")
                            
                            for offset in range(0, word_count, chunk_size // 4):
                                current_addr = start_addr + (offset * 4)
                                remaining_words = min(chunk_size // 4, word_count - offset)
                                
                                progress = (offset * 4 * 100) // size
                                print(f"\rProgress: {progress}% (0x{current_addr:08X})", end='', flush=True)
                                
                                for j in range(remaining_words):
                                    word_addr = current_addr + (j * 4)
                                    if word_addr >= end_addr:
                                        break
                                        
                                    try:
                                        word_data = bdm.read_memory_32(word_addr)
                                        data.extend(word_data.to_bytes(4, 'big'))
                                    except Exception as e:
                                        print(f"\nError at 0x{word_addr:08X}: {e}")
                                        data.extend(b'\x00\x00\x00\x00')
                            
                            data = data[:size]
                            with open(full_path, 'wb') as f:
                                f.write(data)
                            print(f"\rCompleted: {fname} ({len(data)} bytes)")
                        
                        print("\nAll regions dumped successfully!")
                        continue
                    else:
                        print("Unknown region. Use: bootrom, flash, sram, or all")
                        continue
                        
                    # Single region dump
                    full_path = os.path.join(os.getcwd(), filename)
                    size = end - start
                    
                    print(f"Quick dump of {region.upper()} region")
                    print(f"Range: 0x{start:08X} - 0x{end:08X} ({size // 1024}KB)")
                    print(f"Output: {full_path}")
                    
                    confirm = input("Continue? (y/N): ").lower()
                    if confirm == 'y':
                        # Execute the dump directly
                        word_count = (size + 3) // 4
                        chunk_size = 1024
                        data = bytearray()
                        
                        print("Reading memory...")
                        for offset in range(0, word_count, chunk_size // 4):
                            current_addr = start + (offset * 4)
                            remaining_words = min(chunk_size // 4, word_count - offset)
                            
                            progress = (offset * 4 * 100) // size
                            print(f"\rProgress: {progress}% (0x{current_addr:08X})", end='', flush=True)
                            
                            for i in range(remaining_words):
                                word_addr = current_addr + (i * 4)
                                if word_addr >= end:
                                    break
                                    
                                try:
                                    word_data = bdm.read_memory_32(word_addr)
                                    data.extend(word_data.to_bytes(4, 'big'))
                                except Exception as e:
                                    print(f"\nError at 0x{word_addr:08X}: {e}")
                                    data.extend(b'\x00\x00\x00\x00')
                        
                        data = data[:size]
                        with open(full_path, 'wb') as f:
                            f.write(data)
                        print(f"\rCompleted: {filename} ({len(data)} bytes)")
                    else:
                        print("Cancelled.")
                        
                elif cmd == 'rr':
                    if not connected:
                        print("Error: Not connected! Use 'init' first.")
                        continue
                    if len(parts) != 2:
                        print("Usage: rr <register> (d0-d7, a0-a7)")
                        continue
                    try:
                        reg_num = parse_register(parts[1])
                        data = bdm.read_register(reg_num)
                        reg_name = parts[1].upper()
                        print(f"{reg_name} = 0x{data:08X}")
                    except ValueError as e:
                        print(f"Error: {e}")
                    except Exception as e:
                        print(f"BDM Error: {e}")
                        
                elif cmd == 'wr':
                    if not connected:
                        print("Error: Not connected! Use 'init' first.")
                        continue
                    if len(parts) != 3:
                        print("Usage: wr <register> <data> (d0-d7, a0-a7)")
                        continue
                    try:
                        reg_num = parse_register(parts[1])
                        data = parse_hex_value(parts[2])
                        bdm.write_register(reg_num, data)
                        reg_name = parts[1].upper()
                        print(f"{reg_name} = 0x{data:08X}")
                    except ValueError as e:
                        print(f"Error: {e}")
                    except Exception as e:
                        print(f"BDM Error: {e}")
                        
                elif cmd == 'regs':
                    if not connected:
                        print("Error: Not connected! Use 'init' first.")
                        continue
                    try:
                        print("CPU Registers:")
                        print("-" * 40)
                        for i in range(8):
                            d_reg = bdm.read_register(i)
                            a_reg = bdm.read_register(i + 8)
                            print(f"D{i}: 0x{d_reg:08X}    A{i}: 0x{a_reg:08X}")
                    except Exception as e:
                        print(f"BDM Error: {e}")
                        
                else:
                    print(f"Unknown command: {cmd}")
                    print("Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                print("\nUse 'quit' or 'exit' to leave")
                continue
            except EOFError:
                break
                
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        bdm.cleanup()
        print("BDM interface closed.")

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--console':
        bdm_console()
    else:
        # Original test code for backward compatibility
        bdm = MCF54415_BDM()
        
        try:
            print("MCF54415 BDM Interface Test")
            print("Run with --console for interactive mode")
            print("=" * 30)
            
            # Basic connection test
            bdm.reset_target()
            bdm.enter_debug_mode()
            
            if not bdm.bdm_sync():
                print("Failed to sync with target!")
                return
                
            print("BDM connection successful!")
            print("Use 'python3 bdm_interface.py --console' for interactive mode")
            
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            bdm.cleanup()

if __name__ == "__main__":
    main()