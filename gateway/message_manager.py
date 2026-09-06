"""
Async message manager for ESP32-NOW Gateway
Handles message sending, ACK waiting, and retries
"""

import time
import espnow
from utils import log
from config import BURST_COUNT, BURST_INTERVAL_MS, ACK_TIMEOUT_MS, MAX_RETRIES, RETRY_DELAY_MS, BROADCAST_ADDRESS
from network_manager import ensure_peer, _pending_acks, get_pending_acks

class MessageState:
    """State of a message"""
    PENDING = "pending"
    ACKED = "acked"
    RETRYING = "retrying"
    FAILED = "failed"

class MessageManager:
    """Manages async message sending with retries"""
    
    def __init__(self, espnow_instance: espnow.ESPNow):
        self.espnow_instance = espnow_instance
        self.messages = {}  # {msg_id: {'state': MessageState, 'timestamp': int, 'retries': int, 'payload': bytes}}
        self.next_message_id = 1
    
    def send_toggle_async(self) -> int:
        """
        Queue a toggle message for async sending.
        
        Returns:
            int: The message ID
        """
        msg_id = self.next_message_id
        self.next_message_id += 1
        
        payload = b"toggle:" + str(msg_id).encode()
        
        self.messages[msg_id] = {
            'state': MessageState.PENDING,
            'timestamp': time.ticks_ms(),
            'retries': 0,
            'payload': payload
        }
        
        # Add to pending ACKs
        _pending_acks[msg_id] = time.ticks_ms()
        
        log(f"Queued toggle message ID {msg_id} for async sending")
        
        # Send immediately (non-blocking)
        self._send_burst(msg_id, payload)
        
        return msg_id
    
    def _send_burst(self, msg_id: int, payload: bytes) -> None:
        """Send a burst of packets (non-blocking)"""
        log(f"Sending toggle (ID={msg_id}) as burst of {BURST_COUNT} packets")
        
        for i in range(BURST_COUNT):
            self.espnow_instance.send(BROADCAST_ADDRESS, payload)
            time.sleep_ms(BURST_INTERVAL_MS)
    
    def process_acks(self) -> None:
        """
        Process incoming ACKs and update message states.
        Should be called regularly from the main loop.
        """
        # Try to receive ACKs (non-blocking)
        try:
            host, msg = self.espnow_instance.recv(timeout_ms=0)
            if msg and host:
                ensure_peer(self.espnow_instance, host)
                
                if msg.startswith(b'ack:'):
                    try:
                        ack_id = int(msg.split(b':')[1])
                        pending_acks = get_pending_acks()
                        
                        if ack_id in pending_acks:
                            # Remove from pending ACKs
                            if ack_id in pending_acks:
                                del pending_acks[ack_id]
                            
                            # Update message state
                            if ack_id in self.messages:
                                self.messages[ack_id]['state'] = MessageState.ACKED
                                log(f"ACK received for message ID {ack_id}")
                            else:
                                log(f"Received ACK for unknown message ID {ack_id}")
                    except (ValueError, IndexError):
                        pass
        except OSError:
            # No message available
            pass
    
    def process_retries(self) -> None:
        """
        Check for messages that need retrying and resend them.
        Should be called regularly from the main loop.
        """
        current_time = time.ticks_ms()
        
        for msg_id, msg_data in list(self.messages.items()):
            state = msg_data['state']
            timestamp = msg_data['timestamp']
            retries = msg_data['retries']
            
            # Check if message needs retry
            if state == MessageState.PENDING:
                elapsed = time.ticks_diff(current_time, timestamp)
                
                if elapsed >= ACK_TIMEOUT_MS:
                    # Timeout reached, check if we should retry
                    if retries < MAX_RETRIES:
                        msg_data['state'] = MessageState.RETRYING
                        msg_data['retries'] += 1
                        msg_data['timestamp'] = current_time + RETRY_DELAY_MS
                        log(f"Message ID {msg_id} timed out, will retry ({retries + 1}/{MAX_RETRIES})")
                    else:
                        msg_data['state'] = MessageState.FAILED
                        log(f"Message ID {msg_id} failed after {MAX_RETRIES} retries")
                        # Remove from pending ACKs
                        if msg_id in _pending_acks:
                            del _pending_acks[msg_id]
            
            # Retry if it's time
            elif state == MessageState.RETRYING:
                if time.ticks_diff(current_time, timestamp) >= 0:
                    # Time to retry
                    log(f"Retrying message ID {msg_id} (attempt {retries + 1})")
                    msg_data['state'] = MessageState.PENDING
                    msg_data['timestamp'] = current_time
                    # Re-add to pending ACKs
                    _pending_acks[msg_id] = current_time
                    self._send_burst(msg_id, msg_data['payload'])
    
    def cleanup_old_messages(self) -> None:
        """Remove old ACKed messages to prevent memory buildup"""
        current_time = time.ticks_ms()
        to_remove = []
        
        for msg_id, msg_data in self.messages.items():
            if msg_data['state'] == MessageState.ACKED:
                elapsed = time.ticks_diff(current_time, msg_data['timestamp'])
                # Keep ACKed messages for 5 seconds, then remove
                if elapsed > 5000:
                    to_remove.append(msg_id)
            elif msg_data['state'] == MessageState.FAILED:
                elapsed = time.ticks_diff(current_time, msg_data['timestamp'])
                # Keep failed messages for 10 seconds, then remove
                if elapsed > 10000:
                    to_remove.append(msg_id)
        
        for msg_id in to_remove:
            del self.messages[msg_id]
    
    def update(self) -> None:
        """
        Main update function - processes ACKs, retries, and cleanup.
        Should be called regularly from the main loop.
        """
        self.process_acks()
        self.process_retries()
        self.cleanup_old_messages()






