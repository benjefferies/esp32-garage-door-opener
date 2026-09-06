"""SoftAP + tiny HTTP form for first-time / failed Wi-Fi setup."""

import socket
from utils import log
from config import AP_SSID, AP_PASSWORD, AP_IP

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
<form method="post">
<label>SSID</label>
<input name="ssid" autocomplete="off" autocapitalize="none">
<label>Password</label>
<input name="password" type="password">
<button>Save and connect</button>
</form>
<p class="note">Join Wi-Fi <strong>%s</strong>, then open <strong>http://%s</strong>.</p>
"""

SAVED_PAGE = """<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garage WiFi</title>
<p>Saved. The gateway will leave this setup network and join your Wi-Fi.</p>
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


def _http_response(body, status="200 OK"):
    payload = body if isinstance(body, bytes) else body.encode()
    header = "HTTP/1.0 %s\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % (
        status,
        len(payload),
    )
    return header.encode() + payload


def _recv_request(conn):
    conn.settimeout(2)
    data = b""
    while b"\r\n\r\n" not in data and len(data) < 2048:
        chunk = conn.recv(256)
        if not chunk:
            break
        data += chunk
    if b"\r\n\r\n" not in data:
        return "", b""
    head, rest = data.split(b"\r\n\r\n", 1)
    lines = head.split(b"\r\n")
    request_line = lines[0].decode() if lines else ""
    headers = {}
    for line in lines[1:]:
        if b":" in line:
            key, value = line.split(b":", 1)
            headers[key.decode().lower()] = value.strip()
    length = int(headers.get("content-length", b"0") or b"0")
    while len(rest) < length:
        chunk = conn.recv(256)
        if not chunk:
            break
        rest += chunk
    return request_line, rest[:length]


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


def run_portal(reason="Set the home Wi-Fi"):
    import network

    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    if AP_PASSWORD:
        try:
            ap.config(essid=AP_SSID, password=AP_PASSWORD, authmode=3)
        except TypeError:
            ap.config(essid=AP_SSID, password=AP_PASSWORD)
    else:
        try:
            ap.config(essid=AP_SSID, authmode=0)
        except TypeError:
            ap.config(essid=AP_SSID)
    try:
        ap.ifconfig((AP_IP, "255.255.255.0", AP_IP, AP_IP))
    except OSError:
        pass
    log("WiFi setup AP {} (open) — open http://{}".format(AP_SSID, AP_IP))
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
    try:
        while saved is None:
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
                request_line, body = _recv_request(conn)
                method = request_line.split(" ")[0] if request_line else "GET"
                if method == "POST":
                    fields = parse_form_body(body)
                    ssid = (fields.get("ssid") or "").strip()
                    if ssid:
                        saved = (ssid, fields.get("password") or "")
                        conn.send(_http_response(SAVED_PAGE))
                    else:
                        conn.send(_http_response(FORM_PAGE % (reason, AP_SSID, AP_IP)))
                else:
                    conn.send(_http_response(FORM_PAGE % (reason, AP_SSID, AP_IP)))
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
