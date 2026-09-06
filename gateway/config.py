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
# Long timeout to account for opener's sleep cycle and async nature
ACK_TIMEOUT_MS = 10000  # 10 seconds

# Retry parameters
MAX_RETRIES = 3  # Maximum number of retries before giving up
RETRY_DELAY_MS = 1000  # Delay before retrying (1 second)

# How long to keep pending ACKs (in milliseconds)
# ACKs for messages within this window will be accepted even if we've moved on
PENDING_ACK_WINDOW_MS = 15000  # 15 seconds to match retry window 