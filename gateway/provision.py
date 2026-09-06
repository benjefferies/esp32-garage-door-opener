"""SoftAP + tiny HTTP API for first-time / failed Wi-Fi setup."""

import socket

try:
    import ujson as json
except ImportError:
    import json

from utils import log
from config import AP_SSID, AP_PASSWORD, AP_IP, WIFI_CHANNEL

CORS = (
    "Access-Control-Allow-Origin: *\r\n"
    "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
    "Access-Control-Allow-Headers: Content-Type\r\n"
    "Access-Control-Allow-Private-Network: true\r\n"
)

FORM_PAGE = """<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garage WiFi</title>
<style>
body{font-family:sans-serif;background:#12161c;color:#e8edf2;margin:1.5rem}
label,p{display:block;margin:.75rem 0 .25rem}
input{width:100%;padding:.6rem;box-sizing:border-box}
button{margin-top:1rem;padding:.8rem 1rem;width:100%}
.note{color:#9aa6b2;font-size:.9rem}
</style>
<p class="note">%s</p>
<form method="post" action="/api/wifi">
<input type="hidden" name="n" value="%s">
<label>SSID</label>
<input name="ssid" autocomplete="off" autocapitalize="none">
<label>Password</label>
<input name="password" type="password">
<button>Save and connect</button>
</form>
<p class="note">Prefer the Garage web app on this setup network. Join <strong>%s</strong>, then open the app tab.</p>
"""

RETURN_APP_PAGE = """<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garage</title>
<style>
body{font-family:sans-serif;background:#12161c;color:#e8edf2;margin:1.5rem}
.note{color:#9aa6b2}
</style>
<p>Close this Wi-Fi login sheet, then go back to the <strong>Garage</strong> tab.</p>
<p class="note">Do not set Wi-Fi here. The Garage app talks to this gateway after you return.</p>
"""

CAPTIVE_PROBES = {
    "/generate_204": ("", "204 No Content", "text/plain"),
    "/gen_204": ("", "204 No Content", "text/plain"),
    "/hotspot-detect.html": ("Success", "200 OK", "text/html"),
    "/library/test/success.html": ("Success", "200 OK", "text/html"),
    "/success.txt": ("success", "200 OK", "text/plain"),
    "/connecttest.txt": ("Microsoft Connect Test", "200 OK", "text/plain"),
    "/ncsi.txt": ("Microsoft NCSI", "200 OK", "text/plain"),
    "/canonical.html": ("<HTML></HTML>\n", "200 OK", "text/html"),
}

SAVED_PAGE = """<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garage WiFi</title>
<style>
body{font-family:sans-serif;background:#12161c;color:#e8edf2;margin:1.5rem}
.note{color:#9aa6b2}
</style>
<p>Saved. Rejoin home Wi-Fi or cellular, then open the Garage app. Pairing finishes when this gateway is online.</p>
<p class="note">The setup network will turn off in a moment.</p>
"""

NEED_SW1_PAGE = """<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garage WiFi</title>
<p>Press SW1 on the gateway, then submit again.</p>
"""


def url_unquote(text):
    text = text.replace("+", " ")
    out = []
    i = 0
    while i < len(text):
        if text[i] == "%" and i + 2 < len(text):
            try:
                out.append(chr(int(text[i + 1 : i + 3], 16)))
                i += 3
                continue
            except ValueError:
                pass
        out.append(text[i])
        i += 1
    return "".join(out)


def parse_form_body(body):
    if not body:
        return {}
    if isinstance(body, bytes):
        body = body.decode()
    fields = {}
    for part in body.split("&"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        fields[url_unquote(key)] = url_unquote(value)
    return fields


def parse_request_target(request_line):
    if not request_line:
        return "GET", "/", {}
    parts = request_line.split(" ")
    method = parts[0] if parts else "GET"
    raw = parts[1] if len(parts) > 1 else "/"
    if "?" in raw:
        path, query = raw.split("?", 1)
        return method, path, parse_form_body(query)
    return method, raw, {}


def parse_body(body, content_type=""):
    if not body:
        return {}
    text = body.decode() if isinstance(body, bytes) else body
    if "json" in (content_type or ""):
        try:
            data = json.loads(text)
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}
    return parse_form_body(text)


def captive_probe(path):
    clean = (path or "/").split("?")[0].rstrip("/") or "/"
    if not clean.startswith("/"):
        clean = "/" + clean
    if clean in CAPTIVE_PROBES:
        return CAPTIVE_PROBES[clean]
    name = clean.rsplit("/", 1)[-1]
    for probe, payload in CAPTIVE_PROBES.items():
        if probe.endswith("/" + name) or probe == "/" + name:
            return payload
    return None


def wifi_fields(fields):
    ssid = (fields.get("ssid") or "").strip()
    password = fields.get("password") or ""
    nonce = (fields.get("nonce") or fields.get("n") or "").strip()
    return ssid, password, nonce or None


def _http_response(body, status="200 OK", content_type="text/html; charset=utf-8"):
    payload = body if isinstance(body, bytes) else body.encode()
    header = (
        "HTTP/1.0 %s\r\nContent-Type: %s\r\nContent-Length: %d\r\nConnection: close\r\n%s\r\n"
        % (status, content_type, len(payload), CORS)
    )
    return header.encode() + payload


def _json_response(data, status="200 OK"):
    return _http_response(json.dumps(data), status=status, content_type="application/json")


def _recv_request(conn):
    conn.settimeout(2)
    data = b""
    while b"\r\n\r\n" not in data and len(data) < 2048:
        chunk = conn.recv(256)
        if not chunk:
            break
        data += chunk
    if b"\r\n\r\n" not in data:
        return "", {}, b""
    head, rest = data.split(b"\r\n\r\n", 1)
    lines = head.split(b"\r\n")
    request_line = lines[0].decode() if lines else ""
    headers = {}
    for line in lines[1:]:
        if b":" in line:
            key, value = line.split(b":", 1)
            headers[key.decode().lower()] = value.strip().decode()
    try:
        length = int(headers.get("content-length", "0") or "0")
    except ValueError:
        length = 0
    while len(rest) < length:
        chunk = conn.recv(256)
        if not chunk:
            break
        rest += chunk
    return request_line, headers, rest[:length]


def _dns_response(query, ip_bytes):
    if len(query) < 12:
        return None
    flags = query[2:4]
    if flags[0] & 0x78:
        return None
    header = query[:2] + b"\x81\x80" + query[4:6] + b"\x00\x01\x00\x00\x00\x00"
    question = query[12:]
    end = question.find(b"\x00")
    if end < 0 or end + 5 > len(question):
        return None
    question = question[: end + 5]
    answer = b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x1e\x00\x04" + ip_bytes
    return header + question + answer


def _ip_bytes(ip):
    return bytes(int(part) for part in ip.split("."))


def _button_down():
    try:
        from machine import Pin
        from config import BUTTON_PIN

        return Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP).value() == 0
    except ImportError:
        return False


def _start_ap():
    import network
    import time

    sta = network.WLAN(network.STA_IF)
    try:
        sta.disconnect()
    except OSError:
        pass
    sta.active(False)
    time.sleep_ms(200)

    ap = network.WLAN(network.AP_IF)
    ap.active(False)
    time.sleep_ms(200)
    ap.active(True)
    auth = getattr(network, "AUTH_WPA_WPA2_PSK", 4)
    try:
        ap.config(
            essid=AP_SSID,
            password=AP_PASSWORD,
            authmode=auth,
            channel=WIFI_CHANNEL,
        )
    except TypeError:
        ap.config(essid=AP_SSID, password=AP_PASSWORD)
    try:
        ap.ifconfig((AP_IP, "255.255.255.0", AP_IP, AP_IP))
    except OSError:
        pass
    t0 = time.ticks_ms()
    while not ap.active():
        if time.ticks_diff(time.ticks_ms(), t0) > 3000:
            break
        time.sleep_ms(50)
    return sta, ap


def run_portal(reason="Set the home Wi-Fi"):
    sta, ap = _start_ap()
    log(
        "WiFi setup AP {} password {} channel {} — app posts to http://{}".format(
            AP_SSID, AP_PASSWORD, WIFI_CHANNEL, AP_IP
        )
    )
    log(reason)

    http = socket.socket()
    http.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    http.bind(("0.0.0.0", 80))
    http.listen(2)
    http.settimeout(0.2)

    dns = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dns.settimeout(0.05)
    try:
        dns.bind(("0.0.0.0", 53))
    except OSError:
        dns.close()
        dns = None

    ip_bytes = _ip_bytes(AP_IP)
    saved = None
    nonce = None
    sw1_ok = False
    try:
        while saved is None:
            if _button_down():
                sw1_ok = True
            if dns:
                try:
                    packet, addr = dns.recvfrom(256)
                    reply = _dns_response(packet, ip_bytes)
                    if reply:
                        dns.sendto(reply, addr)
                except OSError:
                    pass
            try:
                conn, _addr = http.accept()
            except OSError:
                continue
            try:
                request_line, headers, body = _recv_request(conn)
                method, path, query = parse_request_target(request_line)
                if query.get("n") or query.get("nonce"):
                    nonce = (query.get("n") or query.get("nonce") or "").strip() or nonce
                if method == "OPTIONS":
                    conn.send(_http_response(b"", status="204 No Content", content_type="text/plain"))
                    continue
                probe = captive_probe(path)
                if probe:
                    body, status, content_type = probe
                    conn.send(_http_response(body, status=status, content_type=content_type))
                    continue
                if path == "/api/status":
                    conn.send(
                        _json_response(
                            {
                                "ok": True,
                                "ssid": AP_SSID,
                                "ip": AP_IP,
                                "sw1": sw1_ok,
                                "reason": reason,
                            }
                        )
                    )
                    continue
                if path == "/api/wifi" and method == "POST":
                    fields = parse_body(body, headers.get("content-type", ""))
                    ssid, password, body_nonce = wifi_fields(fields)
                    if body_nonce:
                        nonce = body_nonce
                    if not ssid:
                        conn.send(_json_response({"ok": False, "error": "missing_ssid"}, "400 Bad Request"))
                        continue
                    if nonce and not sw1_ok:
                        wants_html = "json" not in headers.get("content-type", "")
                        if wants_html:
                            conn.send(_http_response(NEED_SW1_PAGE, status="409 Conflict"))
                        else:
                            conn.send(_json_response({"ok": False, "error": "press_sw1"}, "409 Conflict"))
                        continue
                    saved = (ssid, password, nonce)
                    wants_html = "json" not in headers.get("content-type", "")
                    if wants_html:
                        conn.send(_http_response(SAVED_PAGE))
                    else:
                        conn.send(_json_response({"ok": True}))
                    continue
                if path in ("/wifi", "/form"):
                    conn.send(_http_response(FORM_PAGE % (reason, nonce or "", AP_SSID)))
                    continue
                conn.send(_http_response(RETURN_APP_PAGE))
            except OSError as err:
                log("Setup HTTP error: {}".format(err))
            finally:
                try:
                    conn.close()
                except OSError:
                    pass
    finally:
        http.close()
        if dns:
            dns.close()
        ap.active(False)
        log("Setup AP off")
    return saved
