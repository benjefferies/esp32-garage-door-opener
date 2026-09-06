"""ESP-NOW and MQTT payload helpers (CPython-safe)."""


def parse_ack(msg):
    """Parse b'ack:<id>' or b'ack:<id>:<open|closed>'."""
    if not msg or not msg.startswith(b"ack:"):
        return None, None
    parts = msg.split(b":")
    if len(parts) < 2:
        return None, None
    try:
        msg_id = int(parts[1])
    except ValueError:
        return None, None
    state = None
    if len(parts) >= 3:
        state = parts[2].decode()
    return msg_id, state


def parse_state(msg):
    """Parse b'state:open' or b'state:closed'."""
    if not msg or not msg.startswith(b"state:"):
        return None
    state = msg.split(b":", 1)[1].decode()
    if state in ("open", "closed"):
        return state
    return None


def is_toggle_command(msg):
    text = msg.strip().lower()
    return text in (b"toggle", b"1", b"open", b"close") or text.startswith(b"toggle:")
