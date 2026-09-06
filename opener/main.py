"""
ESP32-NOW Garage Door Opener Receiver (optimized ACK + recent message suppression)
"""

import time
from machine import deepsleep, reset_cause, DEEPSLEEP_RESET

from settings import LISTEN_TIME_MS, SLEEP_TIME_MS
from switch import SwitchController
from espnow_manager import ESPNowManager
from message_handler import MessageHandler

def main():
    is_cold_boot = reset_cause() != DEEPSLEEP_RESET
    if is_cold_boot:
        print("Cold boot")
        print("Initializing...")
    else:
        print("Woke from sleep")

    # Initialize components
    switch = SwitchController(is_cold_boot)
    espnow_manager = ESPNowManager(is_cold_boot)
    message_handler = MessageHandler()

    # Listen for LISTEN_TIME_MS ms
    t_start = time.ticks_ms()
    message_received = False

    while time.ticks_diff(time.ticks_ms(), t_start) < LISTEN_TIME_MS:
        host, msg = espnow_manager.receive_message(timeout_ms=50)
        if msg and host:
            print(f"Message received from {host}")
            message_received = message_handler.handle_message(msg, switch, espnow_manager, host)
            if message_received:
                break  # Optional — could listen full window if desired

    print(f"{'Message processed,' if message_received else 'No message,'} sleeping for {SLEEP_TIME_MS} ms...")
    switch.cleanup()  # Ensure switch is off before sleeping
    deepsleep(SLEEP_TIME_MS)

if __name__ == "__main__":
    main()
