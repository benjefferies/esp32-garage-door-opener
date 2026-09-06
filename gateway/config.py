"""
Configuration constants for the ESP32-NOW Gateway
"""

# Network configuration
WIFI_CHANNEL = 6  # Used only if STA connect fails
BROADCAST_ADDRESS = b"\xff\xff\xff\xff\xff\xff"

# Hardware configuration
BUTTON_PIN = 9

# Timing configuration
BOOT_DELAY = 2  # seconds
DEBOUNCE_DELAY = 0.1  # seconds
LOOP_DELAY = 0.05  # seconds
WIFI_CONNECT_TIMEOUT_S = 20
WIFI_PATH = "wifi.json"
AP_SSID = "garage-gw"
AP_PASSWORD = "garage-setup"
AP_IP = "192.168.4.1"
CLEAR_WIFI_HOLD_S = 3

# Burst parameters
BURST_COUNT = 20
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
PAIR_WINDOW_S = 60
