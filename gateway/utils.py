"""
Utility functions for the ESP32-NOW Gateway
"""

import time

def log(msg: str) -> None:
    """
    Log a message with a timestamp.
    
    Args:
        msg (str): The message to log
    """
    print("[{:.3f}] {}".format(time.time(), msg)) 