BDMRipper

Overview

Just a python script POC to use the GPIO pins of a raspberry pi to debug Coldfire series MCUs. Tested using a MCF54415.

Features
	•	GPIO-based bit-banging implementation of the BDM protocol.
	•	Memory read/write operations.
	•	CPU register access and modification.
	•	Memory dumping capabilities (Binary, HEX, and Motorola SREC formats).
	•	Interactive command-line interface with extensive command support.

GPIO Pin Assignments

Signal     Description               Default GPIO Pin
DSI        Data Serial Input        13
DSO	       Data Serial Output      	6
DSCLK	     Data Serial Clock	      19
BKPT	     Breakpoint signal	      26
RESET	     Reset signal	            17

Class MCF54415_BDM
	•	Manages GPIO configuration, low-level bit manipulation, and protocol logic.

Methods
	•	setup_gpio(): Initializes GPIO pins.
	•	cleanup(): Resets GPIO pins on exit.
	•	clock_cycle(): Generates a single clock pulse on DSCLK.
	•	shift_out(data, bit_count): Sends data bits to the target.
	•	shift_in(bit_count): Receives data bits from the target.
	•	send_command(command, data, bits): Sends BDM command sequences.
	•	bdm_sync(): Synchronizes with the target MCU.
	•	reset_target(): Resets the target device.
	•	enter_debug_mode(): Enters debug mode on the target.
	•	read_memory_32(address): Reads a 32-bit word from memory.
	•	write_memory_32(address, data): Writes a 32-bit word to memory.
	•	read_register(reg_num): Reads CPU registers.
	•	write_register(reg_num, data): Writes CPU registers.

Interactive Console Commands

Command	Description
init	Initializes BDM connection
wm	Writes memory at given address
dump	Dumps memory contents
dumpfile	Dumps memory region to file
quickdump	Quickly dumps predefined regions
rr	Reads CPU register
wr	Writes CPU register
regs	Displays all CPU registers
map	Shows MCF54415 memory map

Usage

Run script with:

python3 bdm_interface.py --console

Examples
	•	Connect to target:

init


	•	Write memory:

wm 0x20000000 0xDEADBEEF


	•	Memory dump to file:

dumpfile 0x20000000 0x20001000 sram_dump.bin bin


	•	Quickdump BootROM:

quickdump bootrom



Notes
	•	Ensure GPIO wiring matches pin configuration.
	•	Requires RPi.GPIO Python library installed.
	•	Run as root or with appropriate GPIO permissions.
