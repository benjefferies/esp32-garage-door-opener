"""
ESP32-NOW Gateway: local button + HiveMQ commands to the opener.
"""

import time
from utils import log
from config import (
    BOOT_DELAY,
    LOOP_DELAY,
    MQTT_HEARTBEAT_S,
    CONVEX_HEARTBEAT_S,
    PAIR_CONFIRM_GIVE_UP_S,
    PAIR_CONFIRM_RETRY_S,
    PAIR_WINDOW_S,
)
from network_manager import (
    initialize_wifi,
    initialize_espnow,
    send_toggle_with_ack,
    poll_espnow,
    reset_wifi,
)
from button_handler import ButtonHandler
from mqtt_client import GatewayMqtt
from pair_webhook import post_heartbeat, post_pair_confirmation
from wifi_store import clear_pair_nonce


def _try_confirm_pairing(mqtt, nonce) -> bool:
    log("Confirming SoftAP pairing")
    mqtt.publish_pair_ack(nonce)
    if post_pair_confirmation(nonce):
        log("Pair webhook ok")
        clear_pair_nonce()
        return True
    return False


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
    confirm_nonce = boot_pair_nonce
    confirm_until = time.time() + PAIR_CONFIRM_GIVE_UP_S
    next_confirm = 0
    if sta.isconnected():
        mqtt.connect()
        if confirm_nonce and _try_confirm_pairing(mqtt, confirm_nonce):
            confirm_nonce = None
        elif confirm_nonce:
            next_confirm = time.time() + PAIR_CONFIRM_RETRY_S
    else:
        log("Skipping MQTT (no WiFi)")

    button_handler = ButtonHandler(on_press=on_button, on_long_press=reset_wifi)
    log("Gateway ready. SW1 toggles; release, then hold 3s to reset Wi-Fi")
    next_heartbeat = time.time() + MQTT_HEARTBEAT_S
    next_convex_heartbeat = time.time()

    while True:
        button_handler.handle_button()
        mqtt.check()
        poll_espnow(espnow_instance, mqtt)
        if sta.isconnected() and time.time() >= next_heartbeat:
            if not mqtt.client:
                mqtt.connect()
            mqtt.publish_heartbeat()
            next_heartbeat = time.time() + MQTT_HEARTBEAT_S
        if sta.isconnected() and time.time() >= next_convex_heartbeat:
            post_heartbeat()
            next_convex_heartbeat = time.time() + CONVEX_HEARTBEAT_S
        if confirm_nonce and time.time() >= confirm_until:
            log("SoftAP pairing confirm timed out")
            confirm_nonce = None
        elif confirm_nonce and sta.isconnected() and time.time() >= next_confirm:
            if not mqtt.client:
                mqtt.connect()
            if _try_confirm_pairing(mqtt, confirm_nonce):
                confirm_nonce = None
            else:
                next_confirm = time.time() + PAIR_CONFIRM_RETRY_S

        if state["pending_toggle"]:
            source = state["pending_toggle"]
            state["pending_toggle"] = False
            state["message_id"] += 1
            log("Toggle requested from {}".format(source))
            send_toggle_with_ack(espnow_instance, state["message_id"], mqtt)

        time.sleep(LOOP_DELAY)


if __name__ == "__main__":
    main()
