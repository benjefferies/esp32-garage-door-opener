"""SoftAP + tiny HTTP API for first-time / failed Wi-Fi setup."""

import socket

try:
    import ujson as json
except ImportError:
    import json

from utils import limit_txpower, log
from config import AP_SSID, AP_PASSWORD, AP_IP, AP_DNS, APP_URL, WIFI_CHANNEL, WIFI_TXPOWER_DBM
from wifi_store import save_wifi

CORS = (
    "Access-Control-Allow-Origin: *\r\n"
    "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
    "Access-Control-Allow-Headers: Content-Type\r\n"
    "Access-Control-Allow-Private-Network: true\r\n"
)

PORTAL_STYLE = """
body{font-family:"IBM Plex Sans","Segoe UI",sans-serif;background:#12161c;color:#e8edf2;margin:0;line-height:1.4}
.page{max-width:28rem;margin:0 auto;padding:2rem 1.25rem}
h1{margin:0 0 1.25rem;font-weight:600;font-size:1.5rem}
.card{display:flex;flex-direction:column;gap:.85rem;padding:1.25rem;border:1px solid #2a333d;border-radius:12px;background:#1a2027}
.meta,.lede{margin:0;color:#9aa6b2;font-size:.95rem}
.pills{display:flex;flex-wrap:wrap;gap:.4rem;margin:0 0 1rem}
.pill{font-size:.75rem;padding:.25rem .6rem;border-radius:999px;border:1px solid #1f6a3d;background:#163325;color:#7dffa3}
.pill.wait{border-color:#5a4a2a;background:#2a2416;color:#f0c36a}
a{color:#9ec0ff}
.checklist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:.55rem}
.checklist li{display:grid;grid-template-columns:1.35rem 1fr;gap:.7rem;align-items:center;color:#c5d0d8;font-size:.95rem}
.checklist .done,.checklist .active{color:#e8edf2}
.mark{width:1.35rem;height:1.35rem;border-radius:999px;border:1px solid #3a4552;display:grid;place-items:center;font-size:.75rem}
.done .mark{background:#1f6a3d;border-color:#1f6a3d;color:#d8ffe6}
.active .mark{border-color:#2f6fed transparent transparent;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
label{display:flex;flex-direction:column;gap:.35rem;font-size:.9rem}
input{padding:.7rem .75rem;border:1px solid #3a4552;border-radius:8px;background:#12161c;color:#e8edf2;font:inherit}
button{margin-top:.25rem;min-height:4.5rem;padding:.85rem 1rem;border:0;border-radius:8px;background:#2f6fed;color:#e8edf2;font:inherit;font-size:1.2rem;font-weight:600;width:100%}
"""

CHECK_DONE = '<li class="done"><span class="mark">✓</span><span>Ready to start pairing</span></li><li class="done"><span class="mark">✓</span><span>Connect to WiFi called garage-gw</span></li>'

PORTAL_HOME_PAGE = """<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garage</title>
<style>""" + PORTAL_STYLE + """</style>
<main class="page">
<h1>Garage</h1>
<div class="pills"><span class="pill">garage-gw connected</span><span class="pill wait">Processing</span></div>
<section class="card">
<ul class="checklist">
""" + CHECK_DONE + """
<li class="active"><span class="mark"></span><span>Press pair button</span></li>
<li><span class="mark"></span><span>Setup WiFi on gateway</span></li>
<li><span class="mark"></span><span>Join home Wi-Fi</span></li>
</ul>
<p class="lede">Press the pair button (SW1) on the gateway. This sheet stays open and continues here.</p>
<p class="meta"><a href="/wifi">Continue to Wi-Fi setup</a></p>
</section>
</main>
<script>
function tick(){
  fetch("/api/status").then(function(r){return r.json()}).then(function(j){
    if(j.sw1) location.replace("/wifi");
  }).catch(function(){});
}
setInterval(tick, 800);
tick();
</script>
"""

FORM_PAGE = """<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garage</title>
<style>""" + PORTAL_STYLE + """</style>
<main class="page">
<h1>Garage</h1>
<div class="pills"><span class="pill">garage-gw connected</span><span class="pill wait">Processing</span></div>
<section class="card">
<ul class="checklist">
""" + CHECK_DONE + """
<li class="done"><span class="mark">✓</span><span>Press pair button</span></li>
<li class="active"><span class="mark"></span><span>Setup WiFi on gateway</span></li>
<li><span class="mark"></span><span>Join home Wi-Fi</span></li>
</ul>
<p class="meta">__REASON__</p>
<form method="post" action="/api/wifi">
<input type="hidden" name="n" value="__N__">
<label>Home SSID<input name="ssid" autocomplete="off" autocapitalize="none"></label>
<label>Password<input name="password" type="password"></label>
<button>Save and connect</button>
</form>
</section>
</main>
"""

NEED_SW1_PAGE = """<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garage</title>
<style>""" + PORTAL_STYLE + """</style>
<main class="page">
<h1>Garage</h1>
<div class="pills"><span class="pill">garage-gw connected</span><span class="pill wait">Processing</span></div>
<section class="card">
<ul class="checklist">
""" + CHECK_DONE + """
<li class="active"><span class="mark"></span><span>Press pair button</span></li>
<li><span class="mark"></span><span>Setup WiFi on gateway</span></li>
<li><span class="mark"></span><span>Join home Wi-Fi</span></li>
</ul>
<p class="lede">Press the pair button (SW1). This page saves again when it sees the press.</p>
<form id="f" method="post" action="/api/wifi">
<input type="hidden" name="n" value="__N__">
<input type="hidden" name="ssid" value="__S__">
<input type="hidden" name="password" value="__P__">
<button>Save again</button>
</form>
</section>
</main>
<script>
function tick(){
  fetch("/api/status").then(function(r){return r.json()}).then(function(j){
    if(j.sw1) document.getElementById("f").submit();
  }).catch(function(){});
}
setInterval(tick, 800);
tick();
</script>
"""

SAVED_PAGE = """<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garage</title>
<style>""" + PORTAL_STYLE + """</style>
<main class="page">
<h1>Garage</h1>
<div class="pills"><span class="pill wait">Processing</span><span class="pill">Leaving garage-gw</span></div>
<section class="card">
<ul class="checklist">
""" + CHECK_DONE + """
<li class="done"><span class="mark">✓</span><span>Press pair button</span></li>
<li class="done"><span class="mark">✓</span><span>Setup WiFi on gateway</span></li>
<li class="active"><span class="mark"></span><span>Join home Wi-Fi</span></li>
</ul>
<p class="lede">Saved. Connecting to home Wi-Fi — this setup network will close.</p>
<p class="meta">When the phone leaves garage-gw, open the Garage app.</p>
</section>
</main>
"""

CAPTIVE_PATHS = {
    "/generate_204",
    "/gen_204",
    "/hotspot-detect.html",
    "/library/test/success.html",
    "/success.txt",
    "/connecttest.txt",
    "/ncsi.txt",
    "/canonical.html",
}


def html_escape(text):
    text = "" if text is None else str(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def app_origin():
    try:
        from secrets import APP_URL as secret_url

        if secret_url:
            return str(secret_url).rstrip("/")
    except ImportError:
        pass
    return APP_URL.rstrip("/")


def saved_page():
    return SAVED_PAGE


def setup_app_url():
    return app_origin() + "/#setup?saved=1"


def portal_home_page():
    return PORTAL_HOME_PAGE


def form_page(reason, nonce):
    return FORM_PAGE.replace("__REASON__", html_escape(reason or "")).replace(
        "__N__", html_escape(nonce or "")
    )


def need_sw1_page(nonce, ssid, password):
    return (
        NEED_SW1_PAGE.replace("__N__", html_escape(nonce or ""))
        .replace("__S__", html_escape(ssid or ""))
        .replace("__P__", html_escape(password or ""))
    )


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
    if clean in CAPTIVE_PATHS:
        return True
    name = clean.rsplit("/", 1)[-1]
    for probe in CAPTIVE_PATHS:
        if probe.endswith("/" + name) or probe == "/" + name:
            return True
    return False


def captive_payload(path, user_agent=""):
    ua = (user_agent or "").lower()
    if captive_probe(path) or (
        (path or "/") in ("/", "")
        and (
            "captivenetworksupport" in ua
            or "connectivitycheck" in ua
            or "captiveportallogin" in ua
        )
    ):
        return (portal_home_page(), "200 OK", "text/html")
    return None


def dns_reply(query, ip=None):
    """Answer any A query with the SoftAP IP so captive probes hit this portal."""
    ip = ip or AP_IP
    if not query or len(query) < 12 or query[2] & 0x80:
        return None
    i = 12
    n = len(query)
    while i < n:
        length = query[i]
        if length == 0:
            i += 1
            break
        if length & 0xC0:
            i += 2
            break
        i += 1 + length
    if i + 4 > n:
        return None
    i += 4
    try:
        addr = bytes(int(part) for part in ip.split("."))
    except ValueError:
        return None
    if len(addr) != 4:
        return None
    return (
        query[:2]
        + b"\x81\x80"
        + query[4:6]
        + query[4:6]
        + b"\x00\x00\x00\x00"
        + query[12:i]
        + b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x1e\x00\x04"
        + addr
    )


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


def _http_redirect(url, body):
    payload = body if isinstance(body, bytes) else body.encode()
    header = (
        "HTTP/1.0 303 See Other\r\nLocation: %s\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: %d\r\nConnection: close\r\n%s\r\n"
        % (url, len(payload), CORS)
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
    limit_txpower(ap, WIFI_TXPOWER_DBM)
    try:
        ap.ifconfig((AP_IP, "255.255.255.0", AP_IP, AP_DNS))
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
    try:
        dns.bind(("0.0.0.0", 53))
        dns.settimeout(0)
    except OSError as err:
        log("DNS bind failed: {}".format(err))
        dns = None

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
                    reply = dns_reply(packet)
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
                probe = captive_payload(path, headers.get("user-agent", ""))
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
                    log(
                        "WiFi POST ssid={} sw1={} nonce={}".format(
                            ssid or "-",
                            sw1_ok,
                            "yes" if nonce else "no",
                        )
                    )
                    if not ssid:
                        wants_html = "json" not in headers.get("content-type", "")
                        if wants_html:
                            conn.send(_http_response(form_page("SSID is required", nonce)))
                        else:
                            conn.send(_json_response({"ok": False, "error": "missing_ssid"}, "400 Bad Request"))
                        continue
                    if nonce and not sw1_ok:
                        wants_html = "json" not in headers.get("content-type", "")
                        if wants_html:
                            conn.send(_http_response(need_sw1_page(nonce, ssid, password)))
                        else:
                            conn.send(_json_response({"ok": False, "error": "press_sw1"}, "409 Conflict"))
                        continue
                    saved = (ssid, password, nonce)
                    save_wifi(ssid, password, pair_nonce=nonce)
                    log("Saved Wi-Fi for {}".format(ssid))
                    wants_html = "json" not in headers.get("content-type", "")
                    if wants_html:
                        conn.send(_http_response(saved_page()))
                    else:
                        conn.send(_json_response({"ok": True}))
                    continue
                if path in ("/wifi", "/form"):
                    conn.send(_http_response(form_page(reason, nonce)))
                    continue
                conn.send(_http_response(portal_home_page()))
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
            try:
                dns.close()
            except OSError:
                pass
        if saved:
            import time

            # Let the phone paint "joining home Wi-Fi" before the AP vanishes.
            time.sleep(2)
        ap.active(False)
        log("Setup AP off — phone should leave garage-gw")
    return saved
