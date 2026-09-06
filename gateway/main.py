"""
ESP32-NOW Gateway: local button + HiveMQ commands to the opener.
"""

import time
from utils import log
from config import BOOT_DELAY, LOOP_DELAY
from network_manager import (
    initialize_wifi,
    initialize_espnow,
    send_toggle_with_ack,
    poll_espnow,
)
from button_handler import ButtonHandler
from mqtt_client import GatewayMqtt


def main() -> None:
    time.sleep(BOOT_DELAY)
    sta = initialize_wifi()
    espnow_instance = initialize_espnow()

    mac = sta.config("mac")
    log("Gateway MAC address: " + ":".join("%02x" % b for b in mac))

    state = {"message_id": 0, "pending_toggle": False}

    def request_toggle(source="button"):
        state["pending_toggle"] = source

    mqtt = GatewayMqtt(on_toggle=lambda: request_toggle("mqtt"))
    if sta.isconnected():
        mqtt.connect()
    else:
        log("Skipping MQTT (no WiFi)")

    button_handler = ButtonHandler(on_press=lambda: request_toggle("button"))
    log("Gateway ready. SW1 or publish toggle to garage/opener/cmd")

    while True:
        button_handler.handle_button()
        mqtt.check()
        poll_espnow(espnow_instance, mqtt)

        if state["pending_toggle"]:
            source = state["pending_toggle"]
            state["pending_toggle"] = False
            state["message_id"] += 1
            log("Toggle requested from {}".format(source))
            send_toggle_with_ack(espnow_instance, state["message_id"], mqtt)

        time.sleep(LOOP_DELAY)


if __name__ == "__main__":
    main()
