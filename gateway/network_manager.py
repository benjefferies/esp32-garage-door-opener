"""
Network management for the ESP32-NOW Gateway
"""

import network
import espnow
import time
from utils import log
from protocol import parse_ack, parse_state
from config import (
    WIFI_CHANNEL,
    BROADCAST_ADDRESS,
    BURST_COUNT,
    BURST_INTERVAL_MS,
    ACK_TIMEOUT_MS,
    WIFI_CONNECT_TIMEOUT_S,
    BUTTON_PIN,
    CLEAR_WIFI_HOLD_S,
)
from wifi_store import clear_wifi, load_credentials, save_wifi
from provision import run_portal


def reset_wifi() -> None:
    """Forget saved STA credentials and reboot into the setup AP."""
    clear_wifi()
    log("Wi-Fi reset — rebooting into setup AP")
    time.sleep_ms(200)
    from machine import reset

    reset()


def _clear_wifi_if_button_held() -> None:
    from machine import Pin

    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    if button.value() != 0:
        return
    log("SW1 held — keep holding to forget Wi-Fi")
    t0 = time.ticks_ms()
    while button.value() == 0:
        if time.ticks_diff(time.ticks_ms(), t0) >= CLEAR_WIFI_HOLD_S * 1000:
            clear_wifi()
            log("Forgot saved Wi-Fi")
            return
        time.sleep_ms(50)


def _connect_sta(sta, ssid, password) -> bool:
    log("Connecting to {}".format(ssid))
    sta.active(True)
    try:
        sta.disconnect()
    except OSError:
        pass
    sta.connect(ssid, password)
    t0 = time.ticks_ms()
    while not sta.isconnected():
        if time.ticks_diff(time.ticks_ms(), t0) > WIFI_CONNECT_TIMEOUT_S * 1000:
            log("WiFi connect timed out")
            return False
        time.sleep_ms(250)
    channel = sta.config("channel")
    ip = sta.ifconfig()[0]
    log("WiFi connected ip={} channel={}".format(ip, channel))
    log("Opener WIFI_CHANNEL must match {}".format(channel))
    return True


def initialize_wifi() -> network.WLAN:
    """Connect STA Wi-Fi, or host a local setup AP if that fails."""
    log("Initializing WiFi...")
    try:
        _clear_wifi_if_button_held()
    except ImportError:
        pass

    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    reason = "No Wi-Fi saved yet"
    while True:
        ssid, password = load_credentials()
        if ssid and _connect_sta(sta, ssid, password):
            return sta
        if ssid:
            reason = "Could not join {}".format(ssid)
        ssid, password = run_portal(reason)
        save_wifi(ssid, password)
        log("Saved Wi-Fi for {}".format(ssid))


def initialize_espnow() -> espnow.ESPNow:
    log("Initializing ESP-NOW...")
    e = espnow.ESPNow()
    e.active(True)

    try:
        e.add_peer(BROADCAST_ADDRESS)
        log("Added broadcast peer successfully")
    except OSError as err:
        if err.args[0] == -12395:
            log("Broadcast peer already exists, continuing...")
        else:
            log("Error adding broadcast peer: {}".format(err))
            raise

    log("ESP-NOW initialized successfully")
    return e


def handle_espnow_message(msg, mqtt_client, expected_ack_id=None):
    """Handle an ESP-NOW payload. Returns True if it was the expected ACK."""
    state = parse_state(msg)
    if state:
        log("Reed state {}".format(state))
        if mqtt_client:
            mqtt_client.publish_state(state)
        return False

    ack_id, ack_state = parse_ack(msg)
    if ack_id is None:
        return False

    log("ACK received for message ID {}".format(ack_id))
    if ack_state:
        log("Reed state {}".format(ack_state))
        if mqtt_client:
            mqtt_client.publish_state(ack_state)
    if mqtt_client:
        mqtt_client.publish_ack(ack_id)
    return expected_ack_id is not None and ack_id == expected_ack_id


def send_toggle_with_ack(espnow_instance, msg_id, mqtt_client=None) -> bool:
    payload = b"toggle:" + str(msg_id).encode()

    log("Sending toggle (ID={}) as burst of {} packets".format(msg_id, BURST_COUNT))
    for _ in range(BURST_COUNT):
        espnow_instance.send(BROADCAST_ADDRESS, payload)
        time.sleep_ms(BURST_INTERVAL_MS)

    t_ack_start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t_ack_start) < ACK_TIMEOUT_MS:
        host, msg = espnow_instance.recv(timeout_ms=50)
        if msg and host:
            if handle_espnow_message(msg, mqtt_client, expected_ack_id=msg_id):
                return True

    log("Failed to receive ACK for message ID {}".format(msg_id))
    return False


def poll_espnow(espnow_instance, mqtt_client=None) -> None:
    host, msg = espnow_instance.recv(timeout_ms=0)
    if msg and host:
        handle_espnow_message(msg, mqtt_client)
