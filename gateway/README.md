# ESP32 Garage Door Opener Gateway

Sends ESP-NOW toggles to the opener from **SW1** or from **HiveMQ Cloud** (`garage/opener/cmd`). Web accounts can only toggle after pairing at the gateway.

## Hardware

- Custom C3 board, LiPo seated
- **SW1** (GPIO 9 / BOOT) is the local trigger

## Wi-Fi setup (offline web app)

If STA join fails (or nothing is saved), the gateway starts a local AP. Pairing is meant to stay in the Garage web app:

1. Sign in online and tap **Start pairing** (the service worker caches that tab)
2. In the phone Wi-Fi settings, join **`garage-gw`** (password **`garage-gw`**)
3. Open the same browser tab again — it should still render offline
4. Press **SW1**, then the app `POST`s home SSID/password to `http://192.168.4.1/api/wifi`
5. Rejoin home Wi-Fi or cellular. If the browser landed on the gateway **Saved** page, that tab probes the internet and opens the Garage app when you are back online. The app waits while the gateway joins home Wi-Fi and confirms the nonce. That confirm can take a minute; the pairing window stays open for 15 minutes.

`GET /api/status` and `POST /api/wifi` send CORS headers so the cached HTTPS app can call the SoftAP. If the browser blocks that mixed-content `fetch`, the same form submits as a normal POST to `http://192.168.4.1`.

The setup AP does **not** hijack DNS. DHCP points DNS at `8.8.8.8` so iOS/Android should not open a **192.168.4.1** Wi-Fi login sheet. Captive probes (and the iOS CNA user-agent on `/`) still return Success so a sheet that does appear can dismiss itself. Pairing stays in the Garage app, which talks to `http://192.168.4.1` by IP.

Hold **SW1** for more than 3 seconds at any time to forget `wifi.json` and reboot into the setup AP. The same hold during `Initializing WiFi...` also clears credentials before the first STA attempt.

After `sta.connect()`, the radio uses the **home AP channel**. Set opener `WIFI_CHANNEL` to that number or the door radio will miss packets.

## Secrets

Copy [`secrets.py.example`](secrets.py.example) to `secrets.py` on the device (already gitignored). It holds HiveMQ only. Wi-Fi lives in `wifi.json` from the setup page.

```python
MQTT_HOST = "6976bf6995e243d6be6c1f3634bb4f10.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "gateway"
MQTT_PASSWORD = "CHANGE_ME"
MQTT_CLIENT_ID = "garage-gateway"
```

Do not commit `wifi.json` or `secrets.py`.

## MQTT topics

| Topic | Direction | Payload |
|---|---|---|
| `garage/opener/cmd` | HiveMQ → gateway | `toggle` or `pair:<nonce>` |
| `garage/opener/pair/ack` | gateway → HiveMQ | pairing nonce after SW1 |
| `garage/opener/state` | gateway → HiveMQ (retained) | `open` / `closed` |
| `garage/opener/ack` | gateway → HiveMQ | `ack:<id>` |
| `garage/opener/gateway` | gateway → HiveMQ (retained) | `hb` every 20s; last will `offline` |

The HiveMQ `gateway` user must be allowed to **publish** `garage/opener/pair/ack`. If it is subscribe-only, set `CONVEX_SITE_URL` and `DOOR_WEBHOOK_SECRET` so SW1 can POST `/api/pair` instead.

Test from the HiveMQ console: publish `toggle` to `garage/opener/cmd`.

## Flash

Keep the LiPo on. Gateway is `08:92:72:ce:db:a8`.

```bash
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/secrets.py :secrets.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/config.py :config.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/protocol.py :protocol.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/utils.py :utils.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/wifi_store.py :wifi_store.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/provision.py :provision.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/network_manager.py :network_manager.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/mqtt_client.py :mqtt_client.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/pair_webhook.py :pair_webhook.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/button_handler.py :button_handler.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/main.py :main.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART mkdir :umqtt
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/umqtt/__init__.py :umqtt/__init__.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/umqtt/simple.py :umqtt/simple.py
```
