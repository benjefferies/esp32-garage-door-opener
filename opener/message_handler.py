"""
Message handling for the garage door opener
"""

from settings import MAX_RECENT_IDS

class MessageHandler:
    def __init__(self):
        self.recent_message_ids = []
    
    def handle_message(self, msg, led_controller, espnow_manager, sender_mac):
        if not msg.startswith(b'toggle:'):
            return False
            
        msg_id = int(msg.split(b':')[1])
        
        if msg_id in self.recent_message_ids:
            print(f"Duplicate message ID {msg_id} — ignoring")
            return False
            
        print(f"Processing new toggle! Message ID {msg_id}")
        led_controller.toggle()
        print(f"LED state changed to: {'ON' if led_controller.get_state() else 'OFF'}")
        
        # Add message ID to recent list
        self.recent_message_ids.append(msg_id)
        if len(self.recent_message_ids) > MAX_RECENT_IDS:
            self.recent_message_ids.pop(0)
        
        # Ensure peer exists before sending ACK
        espnow_manager.ensure_peer_for_ack(sender_mac)
        
        # Send ACK
        espnow_manager.send_ack(sender_mac, msg_id)
        return True 