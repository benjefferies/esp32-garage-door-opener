"""
Configuration settings for the ESP32-NOW Garage Door Opener
"""

# Network settings
WIFI_CHANNEL = 6
BROADCAST_ADDRESS = b'\xff\xff\xff\xff\xff\xff'

# Hardware settings
MOSFET_PIN = 5  # GPIO pin for LED
GARAGE_DOOR_PULSE_MS = 500  # Duration of MOSFET pulse in milliseconds

# Timing settings
LISTEN_TIME_MS = 250
SLEEP_TIME_MS = 250

# Message handling settings
MAX_RECENT_IDS = 5 