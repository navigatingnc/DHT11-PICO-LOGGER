# Pico W DHT11 Data Logger

Reads temperature and humidity from a DHT11 sensor and logs it to a CSV file on an SD card using a Raspberry Pi Pico W.

## Hardware

- Raspberry Pi Pico W
- DHT11 sensor (data to GPIO15)
- SD card module (SPI pins: GP10–13)

## Setup

1. Flash your Pico W with MicroPython.
2. Copy all files (main.py, lib/) to the Pico using Thonny or ampy.
3. Connect the Pico to your circuit.
4. Reset or run `main.py` to start logging.

## CSV Format
## chatgpt gen 5.22.25

## Notes

- Timestamps are in seconds since boot.
- You can sync time from Wi-Fi if you want real timestamps.

