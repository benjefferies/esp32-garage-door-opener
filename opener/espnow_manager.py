"""
ESP-NOW networking management for the garage door opener
"""

import network
import espnow
from settings import WIFI_CHANNEL, BROADCAST_ADDRESS

class ESPNowManager:
    def __init__(self, is_cold_boot=False):
        self.known_peers = set()
        self.sta = self._initialize_wifi(is_cold_boot)
        self.espnow = self._initialize_espnow(is_cold_boot)
        self._setup_peers(is_cold_boot)
    
    def _initialize_wifi(self, is_cold_boot):
        if is_cold_boot:
            print("Initializing WiFi...")
        sta = network.WLAN(network.STA_IF)
        sta.active(True)
        sta.config(channel=WIFI_CHANNEL)
        if is_cold_boot:
            print(f"WiFi initialized on channel {WIFI_CHANNEL}")
        return sta
    
    def _initialize_espnow(self, is_cold_boot):
        try:
            e = espnow.ESPNow()
            e.active(False)
            if is_cold_boot:
                print("Cleaned up existing ESP-NOW state")
        except OSError:
            if is_cold_boot:
                print("No existing ESP-NOW state to clean up")
        
        if is_cold_boot:
            print("Initializing ESP-NOW...")
        e = espnow.ESPNow()
        e.active(True)
        if is_cold_boot:
            print("ESP-NOW initialized successfully")
        return e
    
    def _setup_peers(self, is_cold_boot):
        mac = self.sta.config('mac')
        self._add_peer(BROADCAST_ADDRESS, "broadcast", is_cold_boot)
        self._add_peer(mac, "unicast", is_cold_boot)
    
    def _add_peer(self, peer, peer_type, is_cold_boot):
        try:
            self.espnow.add_peer(peer)
            if is_cold_boot:
                print(f"Added {peer_type} peer successfully")
        except OSError as e:
            if e.args[0] == -12395:
                if is_cold_boot:
                    print(f"{peer_type} peer already exists, continuing...")
            else:
                print(f"Error adding {peer_type} peer: {e}")
                raise
    
    def ensure_peer_for_ack(self, sender_mac):
        if sender_mac not in self.known_peers:
            try:
                self.espnow.add_peer(sender_mac)
                print(f"Added peer {sender_mac} for ACK")
                self.known_peers.add(sender_mac)
            except OSError as e:
                if e.args[0] == -12395:
                    self.known_peers.add(sender_mac)
                else:
                    print(f"Error adding peer {sender_mac}: {e}")
                    raise
    
    def send_ack(self, sender_mac, msg_id):
        ack_payload = b'ack:' + str(msg_id).encode()
        print(f"Sending ACK for message ID {msg_id} to {sender_mac}")
        self.espnow.send(sender_mac, ack_payload)
    
    def receive_message(self, timeout_ms=50):
        return self.espnow.recv(timeout_ms=timeout_ms) 