"""
Configuration settings for the ESP32-NOW Garage Door Opener
"""

# Network settings
# Must match the home AP channel once the gateway joins Wi-Fi
WIFI_CHANNEL = 6
BROADCAST_ADDRESS = b"\xff\xff\xff\xff\xff\xff"
# Same XC6206 limit as the gateway. ESP-NOW TX still needs to reach it.
WIFI_TXPOWER_DBM = 8

# Hardware settings
# OC1 pin 1 (anode) is GPIO7; cathode to GND (drive high to close the door contacts)
OCTOCUPLER_PIN = 7
GARAGE_DOOR_PULSE_MS = 2000

# Reed header: magnet present shorts GPIO3 to GND
REED_PIN = 3

# Timing settings. Listen first and longer than sleep so a gateway burst
# is likely to land while the radio is up.
LISTEN_TIME_MS = 400
SLEEP_TIME_MS = 100
STATE_EVERY_N_WAKES = 40

# Message handling settings
MAX_RECENT_IDS = 5
