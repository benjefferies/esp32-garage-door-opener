"""
Message handling for the garage door opener
"""

from settings import MAX_RECENT_IDS


class MessageHandler:
    def __init__(self):
        self.recent_message_ids = []

    def handle_message(self, msg, switch, espnow_manager, sender_mac, reed_state):
        if not msg.startswith(b"toggle:"):
            return False

        msg_id = int(msg.split(b":")[1])

        if msg_id in self.recent_message_ids:
            print("Duplicate message ID {} — ignoring".format(msg_id))
            return False

        print("Processing new toggle! Message ID {}".format(msg_id))
        switch.toggle()

        self.recent_message_ids.append(msg_id)
        if len(self.recent_message_ids) > MAX_RECENT_IDS:
            self.recent_message_ids.pop(0)

        espnow_manager.ensure_peer_for_ack(sender_mac)
        espnow_manager.send_ack(sender_mac, msg_id, reed_state)
        return True
