"""
ESP32-NOW Gateway: local button + HiveMQ commands to the opener.
"""

import time
from utils import log
from config import BOOT_DELAY, LOOP_DELAY, PAIR_WINDOW_S
from network_manager import (
    initialize_wifi,
    initialize_espnow,
    send_toggle_with_ack,
    poll_espnow,
    reset_wifi,
)
from button_handler import ButtonHandler
from mqtt_client import GatewayMqtt
from pair_webhook import post_pair_confirmation
from wifi_store import clear_pair_nonce


def _confirm_pairing(mqtt, nonce) -> None:
    log("Confirming SoftAP pairing")
    mqtt.publish_pair_ack(nonce)
    if post_pair_confirmation(nonce):
        log("Pair webhook ok")
    clear_pair_nonce()


def main() -> None:
    time.sleep(BOOT_DELAY)
    sta, boot_pair_nonce = initialize_wifi()
    espnow_instance = initialize_espnow()

    mac = sta.config("mac")
    log("Gateway MAC address: " + ":".join("%02x" % b for b in mac))

    state = {
        "message_id": 0,
        "pending_toggle": False,
        "pair_nonce": None,
        "pair_deadline": 0,
    }

    def request_toggle(source="button"):
        state["pending_toggle"] = source

    def start_pair(nonce):
        state["pair_nonce"] = nonce
        state["pair_deadline"] = time.time() + PAIR_WINDOW_S
        log("Pairing window open — press SW1")

    def on_button():
        nonce = state["pair_nonce"]
        if nonce and time.time() < state["pair_deadline"]:
            state["pair_nonce"] = None
            log("SW1 pairing confirm")
            mqtt.publish_pair_ack(nonce)
            if post_pair_confirmation(nonce):
                log("Pair webhook ok")
            return
        request_toggle("button")

    mqtt = GatewayMqtt(
        on_toggle=lambda: request_toggle("mqtt"),
        on_pair=start_pair,
    )
    if sta.isconnected():
        mqtt.connect()
        if boot_pair_nonce:
            _confirm_pairing(mqtt, boot_pair_nonce)
    else:
        log("Skipping MQTT (no WiFi)")

    button_handler = ButtonHandler(on_press=on_button, on_long_press=reset_wifi)
    log("Gateway ready. SW1 toggles, hold 3s resets Wi-Fi")

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
