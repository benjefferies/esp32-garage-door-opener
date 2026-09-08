"""HTTPS updates to Convex when the gateway publishes MQTT events."""


def _settings():
    try:
        from secrets import CONVEX_SITE_URL, DOOR_WEBHOOK_SECRET
    except ImportError:
        return None
    if not CONVEX_SITE_URL or not DOOR_WEBHOOK_SECRET:
        return None
    return CONVEX_SITE_URL.rstrip("/"), DOOR_WEBHOOK_SECRET


def _post(path, body) -> bool:
    settings = _settings()
    if not settings:
        return False
    site, secret = settings
    try:
        import urequests
    except ImportError:
        return False

    url = site + path
    try:
        response = urequests.post(
            url,
            json=body,
            headers={"Authorization": "Bearer " + secret},
        )
        ok = 200 <= response.status_code < 300
        response.close()
        return ok
    except Exception as err:
        from utils import log

        log("Convex webhook failed: {}".format(err))
        return False


def post_pair_confirmation(nonce) -> bool:
    return _post("/api/pair", {"nonce": nonce})


def post_door_state(state) -> bool:
    return _post("/api/door-state", {"state": state, "gatewayOnline": True})


def post_heartbeat(online=True) -> bool:
    return _post("/api/door-state", {"gatewayOnline": online})
