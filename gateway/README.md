# ESP32 Garage Door Opener Gateway

Sends ESP-NOW toggles to the opener from **SW1** or from **HiveMQ Cloud** (`garage/opener/cmd`). Web accounts can only toggle after an SW1 pairing confirm.

## Hardware

- Custom C3 board, LiPo seated
- **SW1** (GPIO 9 / BOOT) is the local trigger

## Secrets

Copy [`secrets.py.example`](secrets.py.example) to `secrets.py` on the device (already gitignored).

```python
WIFI_SSID = "your-wifi-ssid"
WIFI_PASSWORD = "your-wifi-password"
MQTT_HOST = "6976bf6995e243d6be6c1f3634bb4f10.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "gateway"
MQTT_PASSWORD = "CHANGE_ME"
MQTT_CLIENT_ID = "garage-gateway"
# Optional HTTP fallback if this HiveMQ user cannot publish pair/ack:
# CONVEX_SITE_URL = "https://marvelous-herring-626.eu-west-1.convex.site"
# DOOR_WEBHOOK_SECRET = "same-as-convex"
```

After `sta.connect()`, the radio uses the **home AP channel**. Set opener `WIFI_CHANNEL` to that number or the door radio will miss packets.

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
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/network_manager.py :network_manager.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/mqtt_client.py :mqtt_client.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/pair_webhook.py :pair_webhook.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/button_handler.py :button_handler.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/main.py :main.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART mkdir :umqtt
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/umqtt/__init__.py :umqtt/__init__.py
poetry run mpremote connect /dev/cu.SLAB_USBtoUART cp gateway/umqtt/simple.py :umqtt/simple.py
```
