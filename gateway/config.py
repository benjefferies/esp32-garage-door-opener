"""
Configuration constants for the ESP32-NOW Gateway
"""

# Network configuration
WIFI_CHANNEL = 6
BROADCAST_ADDRESS = b'\xff\xff\xff\xff\xff\xff'

# Hardware configuration
BUTTON_PIN = 9

# Timing configuration
BOOT_DELAY = 2  # seconds
DEBOUNCE_DELAY = 0.1  # seconds
LOOP_DELAY = 0.05  # seconds

# Burst parameters (optimized)
BURST_COUNT = 20
BURST_INTERVAL_MS = 50

# ACK wait parameters
ACK_TIMEOUT_MS = 500 