"""Optional HTTPS confirm if the HiveMQ user cannot publish pair/ack."""


def post_pair_confirmation(nonce) -> bool:
    try:
        from secrets import CONVEX_SITE_URL, DOOR_WEBHOOK_SECRET
    except ImportError:
        return False
    if not CONVEX_SITE_URL or not DOOR_WEBHOOK_SECRET:
        return False
    try:
        import urequests
    except ImportError:
        return False

    url = CONVEX_SITE_URL.rstrip("/") + "/api/pair"
    try:
        response = urequests.post(
            url,
            json={"nonce": nonce},
            headers={"Authorization": "Bearer " + DOOR_WEBHOOK_SECRET},
        )
        ok = 200 <= response.status_code < 300
        response.close()
        return ok
    except Exception as err:
        from utils import log

        log("Pair webhook failed: {}".format(err))
        return False
