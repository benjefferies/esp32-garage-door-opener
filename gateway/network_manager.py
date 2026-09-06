"""
Network management for the ESP32-NOW Gateway
"""

import network
import espnow
import time
from utils import log
from config import WIFI_CHANNEL, BROADCAST_ADDRESS, BURST_COUNT, BURST_INTERVAL_MS, ACK_TIMEOUT_MS, PENDING_ACK_WINDOW_MS

def initialize_wifi() -> network.WLAN:
    """
    Initialize WiFi in station mode.
    
    Returns:
        network.WLAN: The initialized WiFi station interface
    """
    log("Initializing WiFi...")
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.disconnect()
    sta.config(channel=WIFI_CHANNEL)
    log("WiFi initialized on channel {}".format(WIFI_CHANNEL))
    return sta

# Global set to track known opener peers
_known_opener_peers = set()

# Track recent message IDs that are waiting for ACKs
# Format: {msg_id: timestamp_ms}
_pending_acks = {}

def get_pending_acks():
    """Get the pending ACKs dictionary for external access."""
    return _pending_acks

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

def ensure_peer(espnow_instance: espnow.ESPNow, peer_mac: bytes) -> None:
    """
    Ensure a peer is added to ESP-NOW for receiving messages.
    This must be called BEFORE receiving messages from the peer.
    
    Args:
        espnow_instance (espnow.ESPNow): The ESP-NOW instance
        peer_mac (bytes): The MAC address of the peer to add
    """
    if peer_mac in _known_opener_peers:
        return  # Already added
    
    try:
        espnow_instance.add_peer(peer_mac)
        _known_opener_peers.add(peer_mac)
        log(f"Added peer {peer_mac} for receiving ACKs")
    except OSError as e:
        if e.args[0] == -12395:
            # Peer already exists, which is fine
            _known_opener_peers.add(peer_mac)
        else:
            log(f"Error adding peer {peer_mac}: {e}")

def _cleanup_old_pending_acks():
    """Remove ACKs that are too old from the pending list."""
    current_time = time.ticks_ms()
    expired_ids = [
        msg_id for msg_id, timestamp in _pending_acks.items()
        if time.ticks_diff(current_time, timestamp) > PENDING_ACK_WINDOW_MS
    ]
    for msg_id in expired_ids:
        del _pending_acks[msg_id]

def send_toggle_with_ack(espnow_instance: espnow.ESPNow, msg_id: int) -> None:
    """
    Send a toggle command with burst transmission and wait for ACK.
    
    Args:
        espnow_instance (espnow.ESPNow): The ESP-NOW instance
        msg_id (int): The message ID for tracking
    """
    payload = b"toggle:" + str(msg_id).encode()
    
    log(f"Sending toggle (ID={msg_id}) as burst of {BURST_COUNT} packets")
    
    # Add this message ID to pending ACKs
    _pending_acks[msg_id] = time.ticks_ms()
    _cleanup_old_pending_acks()
    
    ack_received = False
    
    # Send burst and listen simultaneously
    # This allows us to discover the opener's MAC and add it as a peer
    # before it sends the ACK
    for i in range(BURST_COUNT):
        espnow_instance.send(BROADCAST_ADDRESS, payload)
        
        # Try to receive any message to discover opener's MAC
        # This is non-blocking, so we don't delay the burst
        try:
            host, msg = espnow_instance.recv(timeout_ms=0)
            if msg and host:
                # Add any sender as a peer immediately
                ensure_peer(espnow_instance, host)
                log(f"Discovered peer {host} during burst")
                
                # Check if this is an ACK for any pending message
                if msg.startswith(b'ack:'):
                    try:
                        ack_id = int(msg.split(b':')[1])
                        if ack_id in _pending_acks:
                            log(f"ACK received during burst! Message ID {ack_id} confirmed from {host}")
                            # Remove from pending ACKs
                            if ack_id in _pending_acks:
                                del _pending_acks[ack_id]
                            # Only consider it a success if it's the current message
                            if ack_id == msg_id:
                                ack_received = True
                                break
                            else:
                                log(f"Received delayed ACK for message ID {ack_id} (waiting for {msg_id})")
                    except (ValueError, IndexError):
                        pass
        except OSError:
            # No message available, continue
            pass
        
        if ack_received:
            break
            
        time.sleep_ms(BURST_INTERVAL_MS)
    
    # Continue listening for ACK after burst if not received yet
    if not ack_received:
        log(f"Listening for ACK for message ID {msg_id}...")
        t_ack_start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t_ack_start) < ACK_TIMEOUT_MS:
            try:
                host, msg = espnow_instance.recv(timeout_ms=100)
                if msg and host:
                    # CRITICAL: Add peer BEFORE processing message
                    ensure_peer(espnow_instance, host)
                    
                    # Debug: log all received messages
                    log(f"Received message from {host}: {msg}")
                    
                    if msg.startswith(b'ack:'):
                        try:
                            ack_id = int(msg.split(b':')[1])
                            # Accept ACK if it's for any pending message (handles delayed ACKs)
                            if ack_id in _pending_acks:
                                log(f"ACK received for message ID {ack_id} (waiting for {msg_id})")
                                # Remove from pending ACKs
                                if ack_id in _pending_acks:
                                    del _pending_acks[ack_id]
                                # Only consider it a success if it's the current message
                                if ack_id == msg_id:
                                    log(f"ACK matched! Message ID {ack_id} confirmed from {host}")
                                    ack_received = True
                                    break
                                else:
                                    log(f"Received delayed ACK for message ID {ack_id} (waiting for {msg_id})")
                            else:
                                log(f"ACK for unknown message ID {ack_id} (not in pending list)")
                        except (ValueError, IndexError) as e:
                            log(f"Error parsing ACK message: {e}, msg={msg}")
                    else:
                        log(f"Received non-ACK message: {msg}")
            except OSError as e:
                # Timeout or no message available
                # Error code 110 is ETIMEDOUT, which is expected when no message arrives
                if hasattr(e, 'args') and len(e.args) > 0 and e.args[0] != 110:
                    log(f"Error receiving message: {e}")
                continue
    
    if not ack_received:
        log(f"Failed to receive ACK for message ID {msg_id}")
    else:
        # Remove from pending if we got the ACK
        if msg_id in _pending_acks:
            del _pending_acks[msg_id] 