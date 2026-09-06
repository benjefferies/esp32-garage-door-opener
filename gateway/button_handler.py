"""
Button handling for the ESP32-NOW Gateway
"""

try:
    from machine import Pin
except ImportError:
    Pin = None
from utils import log
from config import BUTTON_PIN, DEBOUNCE_DELAY, CLEAR_WIFI_HOLD_S
import time


def held_long_enough(held_ms, threshold_s=CLEAR_WIFI_HOLD_S) -> bool:
    return held_ms >= threshold_s * 1000


class ButtonHandler:
    def __init__(self, on_press, on_long_press=None):
        self.button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
        self.on_press = on_press
        self.on_long_press = on_long_press
        self.pressed_at = None
        self.long_fired = False
        log("Button initialized on GPIO {}".format(BUTTON_PIN))

    def handle_button(self) -> None:
        pressed = self.button.value() == 0
        now = time.ticks_ms()

        if pressed:
            if self.pressed_at is None:
                self.pressed_at = now
                self.long_fired = False
                return
            held = time.ticks_diff(now, self.pressed_at)
            if self.on_long_press and not self.long_fired and held_long_enough(held):
                self.long_fired = True
                log("SW1 held {} ms — reset".format(held))
                self.on_long_press()
            return

        if self.pressed_at is not None and not self.long_fired:
            held = time.ticks_diff(now, self.pressed_at)
            if held >= DEBOUNCE_DELAY * 1000:
                self.on_press()
        self.pressed_at = None
        self.long_fired = False
