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
)


def initialize_wifi() -> network.WLAN:
    """Connect STA Wi-Fi so ESP-NOW shares the AP channel."""
    log("Initializing WiFi...")
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.disconnect()

    try:
        from secrets import WIFI_SSID, WIFI_PASSWORD
    except ImportError:
        log("No secrets.py — ESP-NOW only on channel {}".format(WIFI_CHANNEL))
        sta.config(channel=WIFI_CHANNEL)
        return sta

    if not WIFI_SSID or WIFI_SSID == "your-wifi-ssid":
        log("WIFI_SSID not set — ESP-NOW only on channel {}".format(WIFI_CHANNEL))
        sta.config(channel=WIFI_CHANNEL)
        return sta

    log("Connecting to {}".format(WIFI_SSID))
    sta.connect(WIFI_SSID, WIFI_PASSWORD)
    t0 = time.ticks_ms()
    while not sta.isconnected():
        if time.ticks_diff(time.ticks_ms(), t0) > WIFI_CONNECT_TIMEOUT_S * 1000:
            log("WiFi connect timed out — ESP-NOW only on channel {}".format(WIFI_CHANNEL))
            sta.config(channel=WIFI_CHANNEL)
            return sta
        time.sleep_ms(250)

    channel = sta.config("channel")
    ip = sta.ifconfig()[0]
    log("WiFi connected ip={} channel={}".format(ip, channel))
    log("Opener WIFI_CHANNEL must match {}".format(channel))
    return sta


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
