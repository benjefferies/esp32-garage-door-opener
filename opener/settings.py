"""
Configuration settings for the ESP32-NOW Garage Door Opener
"""

# Network settings
WIFI_CHANNEL = 6
BROADCAST_ADDRESS = b'\xff\xff\xff\xff\xff\xff'

# Hardware settings
# OC1 pin 1 (anode) is GPIO7; cathode to GND (drive high to close the door contacts)
OCTOCUPLER_PIN = 7
GARAGE_DOOR_PULSE_MS = 2000  # Duration of pulse in milliseconds

# Timing settings
LISTEN_TIME_MS = 250
SLEEP_TIME_MS = 250

# Message handling settings
MAX_RECENT_IDS = 5 