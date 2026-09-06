"""
ESP32-NOW Garage Door Opener Receiver
"""

import time
from machine import deepsleep, reset_cause, DEEPSLEEP_RESET

from settings import LISTEN_TIME_MS, SLEEP_TIME_MS
from switch import SwitchController
from espnow_manager import ESPNowManager
from message_handler import MessageHandler
from reed import ReedSensor


def main():
    is_cold_boot = reset_cause() != DEEPSLEEP_RESET
    if is_cold_boot:
        print("Cold boot")
        print("Initializing...")
    else:
        print("Woke from sleep")

    switch = SwitchController(is_cold_boot)
    espnow_manager = ESPNowManager(is_cold_boot)
    message_handler = MessageHandler()
    reed = ReedSensor()

    changed = reed.take_if_changed()
    if changed:
        print("Reed {}".format(changed))
        espnow_manager.send_state(changed)

    t_start = time.ticks_ms()
    message_received = False

    while time.ticks_diff(time.ticks_ms(), t_start) < LISTEN_TIME_MS:
        host, msg = espnow_manager.receive_message(timeout_ms=50)
        if msg and host:
            print("Message received from {}".format(host))
            message_received = message_handler.handle_message(
                msg, switch, espnow_manager, host, reed.read_name()
            )
            if message_received:
                break

    print(
        "{} sleeping for {} ms...".format(
            "Message processed," if message_received else "No message,",
            SLEEP_TIME_MS,
        )
    )
    switch.cleanup()
    deepsleep(SLEEP_TIME_MS)


if __name__ == "__main__":
    main()
