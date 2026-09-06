"""
Configuration constants for the ESP32-NOW Gateway
"""

# Network configuration
WIFI_CHANNEL = 6  # Used only if STA connect fails
BROADCAST_ADDRESS = b"\xff\xff\xff\xff\xff\xff"
# XC6206 is ~250 mA. Default ~20 dBm TX is 280–350 mA. 8 dBm is enough
# for a phone next to SoftAP; raise if home Wi-Fi is far.
WIFI_TXPOWER_DBM = 8

# Hardware configuration
BUTTON_PIN = 9

# Timing configuration
BOOT_DELAY = 2  # seconds
DEBOUNCE_DELAY = 0.1  # seconds
LOOP_DELAY = 0.05  # seconds
WIFI_CONNECT_TIMEOUT_S = 20
WIFI_PATH = "wifi.json"
AP_SSID = "garage-gw"
AP_PASSWORD = "garage-gw"  # WPA2; iPhones often refuse an open ESP32 AP
AP_IP = "192.168.4.1"
AP_DNS = "8.8.8.8"  # Do not point DHCP DNS at the AP or iOS opens a login sheet
APP_URL = "https://garage-opener-rose.vercel.app"
CLEAR_WIFI_HOLD_S = 3

# Burst parameters. Opener listen duty is short, so cover >1 sleep cycle.
BURST_COUNT = 40
BURST_INTERVAL_MS = 50

# Opener sleeps 250ms and pulses ~2s before ACK
ACK_TIMEOUT_MS = 10000

# MQTT topics (HiveMQ Cloud Serverless)
MQTT_KEEPALIVE_S = 60
MQTT_TOPIC_CMD = "garage/opener/cmd"
MQTT_TOPIC_STATE = "garage/opener/state"
MQTT_TOPIC_ACK = "garage/opener/ack"
MQTT_TOPIC_STATUS = "garage/opener/gateway"
MQTT_TOPIC_PAIR_ACK = "garage/opener/pair/ack"
MQTT_HEARTBEAT_S = 20
PAIR_WINDOW_S = 60
PAIR_CONFIRM_RETRY_S = 10
PAIR_CONFIRM_GIVE_UP_S = 15 * 60
