"""
Utility functions for the ESP32-NOW Gateway
"""

import time

def limit_txpower(wlan, dbm) -> None:
    """Cap Wi-Fi TX so the 3.3 V LDO does not brown out."""
    try:
        wlan.config(txpower=dbm)
    except TypeError:
        try:
            wlan.config(txpower=int(dbm))
        except (OSError, ValueError, TypeError, AttributeError) as err:
            log("WiFi txpower not set: {}".format(err))
            return
    except (OSError, ValueError, AttributeError) as err:
        log("WiFi txpower not set: {}".format(err))
        return
    try:
        log("WiFi txpower {} dBm".format(wlan.config("txpower")))
    except (OSError, ValueError, TypeError, AttributeError):
        log("WiFi txpower set {} dBm".format(dbm))


def log(msg: str) -> None:
    """
    Log a message with a timestamp.
    
    Args:
        msg (str): The message to log
    """
    print("[{:.3f}] {}".format(time.time(), msg)) 