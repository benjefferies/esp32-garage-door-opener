"""Load and save STA credentials on the device flash."""

try:
    import ujson as json
except ImportError:
    import json

from config import WIFI_PATH


def _read(path=None):
    try:
        with open(path or WIFI_PATH) as handle:
            data = json.loads(handle.read())
    except (OSError, ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def load_wifi(path=None):
    data = _read(path)
    if not data:
        return None, None
    ssid = data.get("ssid")
    password = data.get("password")
    if not ssid:
        return None, None
    return ssid, password or ""


def peek_pair_nonce(path=None):
    data = _read(path)
    if not data:
        return None
    nonce = data.get("pair_nonce")
    return nonce or None


def save_wifi(ssid, password, pair_nonce=None, path=None) -> None:
    data = {"ssid": ssid, "password": password or ""}
    if pair_nonce:
        data["pair_nonce"] = pair_nonce
    with open(path or WIFI_PATH, "w") as handle:
        handle.write(json.dumps(data))


def clear_pair_nonce(path=None) -> None:
    ssid, password = load_wifi(path)
    if ssid:
        save_wifi(ssid, password, path=path)


def clear_wifi(path=None) -> None:
    try:
        import os

        os.remove(path or WIFI_PATH)
    except OSError:
        pass


def load_credentials():
    return load_wifi()
