"""SoftAP + tiny HTTP API for first-time / failed Wi-Fi setup."""

import socket

try:
    import ujson as json
except ImportError:
    import json

from utils import log
from config import AP_SSID, AP_PASSWORD, AP_IP, AP_DNS, APP_URL, WIFI_CHANNEL
from wifi_store import save_wifi

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

PORTAL_HOME_PAGE = """<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garage</title>
<style>
body{font-family:"IBM Plex Sans","Segoe UI",sans-serif;background:#12161c;color:#e8edf2;margin:0}
.page{max-width:28rem;margin:0 auto;padding:2rem 1.25rem}
.card{padding:1.25rem;border:1px solid #2a333d;border-radius:12px;background:#1a2027}
h1{margin:0 0 1.25rem;font-weight:600;font-size:1.5rem}
p{color:#9aa6b2;line-height:1.4}
</style>
<main class="page">
<h1>Garage</h1>
<section class="card">
<p id="msg">Press the pair button (SW1) on the gateway. This page continues here — the phone login sheet cannot close itself.</p>
</section>
</main>
<script>
var APP="__APP__";
function tick(){
  fetch("/api/status").then(function(r){return r.json()}).then(function(j){
    if(j.sw1) location.replace("/wifi");
  }).catch(function(){});
  fetch(APP+"/manifest.webmanifest?online="+Date.now(),{mode:"no-cors",cache:"no-store"}).then(function(){
    location.replace(APP+"/#setup");
  }).catch(function(){});
}
setInterval(tick, 800);
tick();
</script>
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
<title>Garage</title>
<style>
body{font-family:"IBM Plex Sans","Segoe UI",sans-serif;background:#12161c;color:#e8edf2;margin:0}
.page{max-width:28rem;margin:0 auto;padding:2rem 1.25rem}
.card{padding:1.25rem;border:1px solid #2a333d;border-radius:12px;background:#1a2027}
h1{margin:0 0 1.25rem;font-weight:600;font-size:1.5rem}
p{color:#9aa6b2;line-height:1.4}
.pills{display:flex;flex-wrap:wrap;gap:.4rem;margin:0 0 1rem}
.pill{font-size:.75rem;padding:.25rem .6rem;border-radius:999px;border:1px solid #3a4552;color:#9aa6b2}
.pill.on{border-color:#1f6a3d;background:#163325;color:#7dffa3}
.pill.off{border-color:#5a3a3a;background:#2a1c1c;color:#ff8a8a}
.pill.wait{border-color:#5a4a2a;background:#2a2416;color:#f0c36a}
</style>
<main class="page">
<h1>Garage</h1>
<div class="pills">
<span id="gw" class="pill wait">garage-gw checking</span>
<span id="net" class="pill wait">Checking network…</span>
</div>
<section class="card">
<p>Saved. Opening the Garage app.</p>
<p id="hint">If this tab stays here, rejoin home Wi-Fi or cellular.</p>
</section>
</main>
<script>
var APP="__APP__";
location.replace(APP+"/#setup?saved=1");
function setPill(id, on, text){
  var el=document.getElementById(id);
  el.className="pill "+(on===true?"on":on===false?"off":"wait");
  el.textContent=text;
}
function pingGw(){
  return fetch("/api/status",{cache:"no-store"}).then(function(r){return r.ok}).catch(function(){return false});
}
function pingNet(){
  return fetch(APP+"/manifest.webmanifest?online="+Date.now(),{mode:"no-cors",cache:"no-store"}).then(function(){return true}).catch(function(){return false});
}
function tick(){
  Promise.all([pingGw(), pingNet()]).then(function(pair){
    var gw=pair[0], net=pair[1];
    setPill("gw", gw, gw?"garage-gw connected":"garage-gw not connected");
    setPill("net", net, net?"Online":"Offline");
    document.getElementById("hint").textContent=gw
      ?"Switch to home Wi-Fi or cellular."
      :net?"Online — opening Garage":"Waiting for home Wi-Fi or cellular…";
    if(net) location.replace(APP+"/#setup?saved=1");
  });
}
setInterval(tick, 1500);
tick();
</script>
"""

NEED_SW1_PAGE = """<!doctype html>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Garage</title>
<style>
body{font-family:"IBM Plex Sans","Segoe UI",sans-serif;background:#12161c;color:#e8edf2;margin:0}
.page{max-width:28rem;margin:0 auto;padding:2rem 1.25rem}
.card{padding:1.25rem;border:1px solid #2a333d;border-radius:12px;background:#1a2027}
h1{margin:0 0 1.25rem;font-weight:600;font-size:1.5rem}
p{color:#9aa6b2;line-height:1.4}
button{margin-top:1rem;padding:.85rem 1rem;width:100%;border:0;border-radius:8px;background:#2f6fed;color:#e8edf2;font:inherit;font-weight:600}
</style>
<main class="page">
<h1>Garage</h1>
<section class="card">
<p>Press the pair button (SW1) on the gateway. This page saves again when it sees the press.</p>
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
</script>
"""


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
    return SAVED_PAGE.replace("__APP__", app_origin())


def setup_app_url():
    return app_origin() + "/#setup?saved=1"


def portal_home_page():
    return PORTAL_HOME_PAGE.replace("__APP__", app_origin())


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
    if clean in CAPTIVE_PROBES:
        return CAPTIVE_PROBES[clean]
    name = clean.rsplit("/", 1)[-1]
    for probe, payload in CAPTIVE_PROBES.items():
        if probe.endswith("/" + name) or probe == "/" + name:
            return payload
    return None


def captive_payload(path, user_agent=""):
    probe = captive_probe(path)
    if probe:
        return probe
    ua = (user_agent or "").lower()
    if (path or "/") in ("/", "") and (
        "captivenetworksupport" in ua
        or "connectivitycheck" in ua
        or "captiveportallogin" in ua
    ):
        return ("Success", "200 OK", "text/html")
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

    saved = None
    nonce = None
    sw1_ok = False
    try:
        while saved is None:
            if _button_down():
                sw1_ok = True
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
                    if not ssid:
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
                        conn.send(_http_redirect(setup_app_url(), saved_page()))
                    else:
                        conn.send(_json_response({"ok": True}))
                    continue
                if path in ("/wifi", "/form"):
                    conn.send(_http_response(FORM_PAGE % (reason, nonce or "", AP_SSID)))
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
        ap.active(False)
        log("Setup AP off")
    return saved
