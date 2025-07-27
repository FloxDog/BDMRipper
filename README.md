# BDMRipper

## Overview

A Python script POC which lets me use a raspberry pi 2 as a BDM debugger 

## Features

- GPIO-based bit-banging implementation of the BDM protocol.
- Memory read/write operations.
- CPU register access and modification.
- Memory dumping capabilities (Binary, HEX, and Motorola SREC formats).
- Interactive command-line interface with extensive command support.

## GPIO Pin Assignments

| Signal | Description        | Default GPIO Pin |
| ------ | ------------------ | ---------------- |
| DSI    | Data Serial Input  | 13               |
| DSO    | Data Serial Output | 6                |
| DSCLK  | Data Serial Clock  | 19               |
| BKPT   | Breakpoint signal  | 26               |
| RESET  | Reset signal       | 17               |


## Interactive Console Commands

| Command     | Description                      |
| ----------- | -------------------------------- |
| `init`      | Initializes BDM connection       |
| `wm`        | Writes memory at given address   |
| `dump`      | Dumps memory contents            |
| `dumpfile`  | Dumps memory region to file      |
| `quickdump` | Quickly dumps predefined regions |
| `rr`        | Reads CPU register               |
| `wr`        | Writes CPU register              |
| `regs`      | Displays all CPU registers       |
| `map`       | Shows MCF54415 memory map        |

## Usage

Run script with:

```bash
python3 bdm_interface.py --console
```

### Examples

- **Connect to target**:

  ```
  init
  ```

- **Write memory**:

  ```
  wm 0x20000000 0xDEADBEEF
  ```

- **Memory dump to file**:

  ```
  dumpfile 0x20000000 0x20001000 sram_dump.bin bin
  ```

- **Quickdump BootROM**:

  ```
  quickdump bootrom
  ```

## Notes

- Ensure GPIO wiring matches pin configuration.
- Requires RPi.GPIO Python library installed.
- Run as root or with appropriate GPIO permissions.

