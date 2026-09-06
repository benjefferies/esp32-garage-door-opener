"""Load and save STA credentials on the device flash."""

try:
    import ujson as json
except ImportError:
    import json

from config import WIFI_PATH


def load_wifi(path=None):
    try:
        with open(path or WIFI_PATH) as handle:
            data = json.loads(handle.read())
    except (OSError, ValueError, TypeError):
        return None, None
    ssid = data.get("ssid") if isinstance(data, dict) else None
    password = data.get("password") if isinstance(data, dict) else None
    if not ssid:
        return None, None
    return ssid, password or ""


def save_wifi(ssid, password, path=None) -> None:
    with open(path or WIFI_PATH, "w") as handle:
        handle.write(json.dumps({"ssid": ssid, "password": password or ""}))


def clear_wifi(path=None) -> None:
    try:
        import os

        os.remove(path or WIFI_PATH)
    except OSError:
        pass


def load_credentials():
    ssid, password = load_wifi()
    if ssid:
        return ssid, password
    try:
        from secrets import WIFI_SSID, WIFI_PASSWORD
    except ImportError:
        return None, None
    if not WIFI_SSID or WIFI_SSID == "your-wifi-ssid":
        return None, None
    return WIFI_SSID, WIFI_PASSWORD
