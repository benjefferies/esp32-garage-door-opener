"""
ESP32-NOW Gateway for Garage Door Control (async messaging with retries)
"""

import time
from utils import log
from config import BOOT_DELAY, LOOP_DELAY
from network_manager import initialize_wifi, initialize_espnow
from message_manager import MessageManager
from button_handler import ButtonHandler

def main() -> None:
    time.sleep(BOOT_DELAY)
    sta = initialize_wifi()
    espnow_instance = initialize_espnow()
    
    mac = sta.config('mac')
    # FIXED MAC LOGGING LINE (MicroPython safe)
    log("Gateway MAC address: " + ':'.join('%02x' % b for b in mac))
    
    log("ESP-NOW sender ready. Press the button to toggle the garage door.")
    
    # Create message manager for async messaging
    message_manager = MessageManager(espnow_instance)
    button_handler = ButtonHandler(message_manager)
    
    while True:
        # Handle button (non-blocking)
        button_handler.handle_button()
        
        # Update message manager (processes ACKs, retries, cleanup)
        message_manager.update()
        
        time.sleep(LOOP_DELAY)

if __name__ == "__main__":
    main()