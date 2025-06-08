"""
ESP32-NOW Gateway for Garage Door Control (optimized burst send + ACK, fixed MAC logging)
"""

import time
from utils import log
from config import BOOT_DELAY
from network_manager import initialize_wifi, initialize_espnow
from button_handler import ButtonHandler

def main() -> None:
    time.sleep(BOOT_DELAY)
    sta = initialize_wifi()
    espnow_instance = initialize_espnow()
    
    mac = sta.config('mac')
    # FIXED MAC LOGGING LINE (MicroPython safe)
    log("Gateway MAC address: " + ':'.join('%02x' % b for b in mac))
    
    log("ESP-NOW sender ready. Press the button to toggle the garage door.")
    
    button_handler = ButtonHandler(espnow_instance)
    
    while True:
        button_handler.handle_button()

if __name__ == "__main__":
    main()