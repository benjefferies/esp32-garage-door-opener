"""
Network management for the ESP32-NOW Gateway
"""

import network
import espnow
import time
from utils import limit_txpower, log
from protocol import parse_ack, parse_state
from config import (
    WIFI_CHANNEL,
    BROADCAST_ADDRESS,
    BURST_COUNT,
    BURST_INTERVAL_MS,
    ACK_TIMEOUT_MS,
    WIFI_CONNECT_TIMEOUT_S,
    WIFI_CONNECT_RETRIES,
    WIFI_TXPOWER_DBM,
    BUTTON_PIN,
)
from wifi_store import clear_wifi, load_credentials, peek_pair_nonce, save_wifi
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
    # GPIO9 is also BOOT. USB serial open / DTR-RTS reset often leaves it
    # low, which used to delete wifi.json on every debug plug-in.
    # Forget Wi-Fi with a 3s hold after boot (button_handler), not here.
    if button.value() == 0:
        log("SW1 already down at boot — ignored (release, then hold 3s to forget Wi-Fi)")


def _reboot_to_join() -> None:
    """SoftAP → STA on the same boot often fails; a reset joins from wifi.json."""
    log("Rebooting to join home Wi-Fi")
    time.sleep_ms(500)
    try:
        from machine import reset

        reset()
    except ImportError:
        pass


def _connect_sta(sta, ssid, password) -> bool:
    log("Connecting to {}".format(ssid))
    try:
        sta.active(False)
        time.sleep_ms(300)
    except OSError:
        pass
    sta.active(True)
    time.sleep_ms(300)
    try:
        sta.disconnect()
    except OSError:
        pass
    limit_txpower(sta, WIFI_TXPOWER_DBM)
    try:
        sta.scan()
    except OSError:
        pass
    sta.connect(ssid, password)
    t0 = time.ticks_ms()
    while not sta.isconnected():
        if time.ticks_diff(time.ticks_ms(), t0) > WIFI_CONNECT_TIMEOUT_S * 1000:
            try:
                status = sta.status()
            except OSError:
                status = "?"
            log("WiFi connect timed out status={}".format(status))
            return False
        time.sleep_ms(250)
    try:
        sta.config(pm=getattr(network.WLAN, "PM_NONE", 0))
    except (OSError, ValueError, AttributeError):
        pass
    channel = sta.config("channel")
    ip = sta.ifconfig()[0]
    log("WiFi connected ip={} channel={}".format(ip, channel))
    log("Opener WIFI_CHANNEL must match {}".format(channel))
    return True


def initialize_wifi():
    """Connect STA Wi-Fi, or host a local setup AP if that fails.

    Returns (sta, pair_nonce). pair_nonce is set when the offline web app
    posted credentials during SoftAP pairing.
    """
    log("Initializing WiFi...")
    try:
        _clear_wifi_if_button_held()
    except ImportError:
        pass

    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    reason = "No Wi-Fi saved yet"
    pair_nonce = peek_pair_nonce()
    while True:
        ssid, password = load_credentials()
        if ssid:
            for attempt in range(1, WIFI_CONNECT_RETRIES + 1):
                log("STA join {}/{}".format(attempt, WIFI_CONNECT_RETRIES))
                if _connect_sta(sta, ssid, password):
                    return sta, peek_pair_nonce() or pair_nonce
                time.sleep_ms(1500)
            reason = "Could not join {}".format(ssid)
        saved = run_portal(reason)
        if not saved:
            continue
        ssid, password, portal_nonce = saved
        if portal_nonce:
            pair_nonce = portal_nonce
        save_wifi(ssid, password, pair_nonce=pair_nonce)
        log("Saved Wi-Fi for {}".format(ssid))
        _reboot_to_join()


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
    sent = 0
    for _ in range(BURST_COUNT):
        try:
            if espnow_instance.send(BROADCAST_ADDRESS, payload):
                sent += 1
        except OSError as err:
            log("ESP-NOW send failed: {}".format(err))
            break
        time.sleep_ms(BURST_INTERVAL_MS)
    log("ESP-NOW sent {}/{}".format(sent, BURST_COUNT))

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
