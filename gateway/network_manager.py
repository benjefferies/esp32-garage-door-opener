"""
Network management for the ESP32-NOW Gateway
"""

import network
import espnow
import time
from utils import log
from config import WIFI_CHANNEL, BROADCAST_ADDRESS, BURST_COUNT, BURST_INTERVAL_MS, ACK_TIMEOUT_MS

def initialize_wifi() -> network.WLAN:
    """
    Initialize WiFi in station mode.
    
    Returns:
        network.WLAN: The initialized WiFi station interface
    """
    log("Initializing WiFi...")
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.config(channel=WIFI_CHANNEL)
    log("WiFi initialized")
    return sta

def initialize_espnow() -> espnow.ESPNow:
    """
    Initialize ESP-NOW and add broadcast peer.
    
    Returns:
        espnow.ESPNow: The initialized ESP-NOW instance
    """
    log("Initializing ESP-NOW...")
    e = espnow.ESPNow()
    e.active(True)
    
    try:
        e.add_peer(BROADCAST_ADDRESS)
        log("Added broadcast peer successfully")
    except OSError as e:
        if e.args[0] == -12395:
            log("Broadcast peer already exists, continuing...")
        else:
            log("Error adding broadcast peer: {}".format(e))
            raise
    
    log("ESP-NOW initialized successfully")
    return e

def send_toggle_with_ack(espnow_instance: espnow.ESPNow, msg_id: int) -> None:
    """
    Send a toggle command with burst transmission and wait for ACK.
    
    Args:
        espnow_instance (espnow.ESPNow): The ESP-NOW instance
        msg_id (int): The message ID for tracking
    """
    payload = b"toggle:" + str(msg_id).encode()
    
    log(f"Sending toggle (ID={msg_id}) as burst of {BURST_COUNT} packets")
    for i in range(BURST_COUNT):
        espnow_instance.send(BROADCAST_ADDRESS, payload)
        time.sleep_ms(BURST_INTERVAL_MS)
    
    # Wait for ACK after burst
    ack_received = False
    t_ack_start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t_ack_start) < ACK_TIMEOUT_MS:
        host, msg = espnow_instance.recv(timeout_ms=50)
        if msg and host:
            if msg.startswith(b'ack:'):
                ack_id = int(msg.split(b':')[1])
                if ack_id == msg_id:
                    log(f"ACK received for message ID {ack_id} from {host}")
                    ack_received = True
                    break
    
    if not ack_received:
        log(f"Failed to receive ACK for message ID {msg_id}") 