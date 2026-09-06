#!/usr/bin/env bash
# Flash MicroPython onto an ESP32-S3 (matches project stubs v1.25.0).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${1:-/dev/cu.usbmodem2101}"
FIRMWARE="${ROOT}/firmware/ESP32_GENERIC_S3-20250415-v1.25.0.bin"

if [[ ! -f "$FIRMWARE" ]]; then
  echo "Firmware not found at: $FIRMWARE"
  echo "Download it from: https://micropython.org/download/ESP32_GENERIC_S3/"
  exit 1
fi

echo "Using port: $PORT"
echo
echo "If flashing fails, put the board in download mode:"
echo "  1. Hold BOOT"
echo "  2. Tap RESET (or unplug/replug USB once while holding BOOT)"
echo "  3. Release BOOT"
echo

esptool.py --chip esp32s3 --port "$PORT" --before usb_reset erase_flash
esptool.py --chip esp32s3 --port "$PORT" --before usb_reset --baud 460800 write_flash 0 "$FIRMWARE"

echo
echo "MicroPython flashed. Opening REPL (Ctrl+C to exit)..."
poetry -C "$ROOT" run mpremote connect "$PORT" repl
