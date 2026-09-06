# ESP32 Garage Door Opener Gateway

Sends ESP-NOW toggles to the opener from **SW1** or from **HiveMQ Cloud** (`garage/opener/cmd`). Web accounts can only toggle after an SW1 pairing confirm.

## Hardware

- Custom C3 board, LiPo seated
- **SW1** (GPIO 9 / BOOT) is the local trigger

## Wi-Fi setup

If STA join fails (or nothing is saved), the gateway starts a local AP:

1. Join **`garage-gw`** / password **`garage-setup`**
2. Open **http://192.168.4.1** (phones often pop a captive-portal sheet)
3. Enter the home SSID and password
4. The board writes `wifi.json` and tries STA again

Hold **SW1** for 3 seconds during `Initializing WiFi...` to forget `wifi.json` and reopen the setup AP.

After `sta.connect()`, the radio uses the **home AP channel**. Set opener `WIFI_CHANNEL` to that number or the door radio will miss packets.

## Secrets

Copy [`secrets.py.example`](secrets.py.example) to `secrets.py` on the device (already gitignored). Wi-Fi in that file is optional now; HiveMQ still lives there.

```python
WIFI_SSID = ""
WIFI_PASSWORD = ""
MQTT_HOST = "6976bf6995e243d6be6c1f3634bb4f10.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "gateway"
MQTT_PASSWORD = "CHANGE_ME"
MQTT_CLIENT_ID = "garage-gateway"
```

Do not commit `wifi.json`.

## MQTT topics

| Topic | Direction | Payload |
|---|---|---|
| `garage/opener/cmd` | HiveMQ → gateway | `toggle` or `pair:<nonce>` |
| `garage/opener/pair/ack` | gateway → HiveMQ | pairing nonce after SW1 |
| `garage/opener/state` | gateway → HiveMQ (retained) | `open` / `closed` |
| `garage/opener/ack` | gateway → HiveMQ | `ack:<id>` |
| `garage/opener/gateway` | last will | `online` / `offline` |

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
