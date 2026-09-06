"""
Button handling for the ESP32-NOW Gateway
"""

from machine import Pin
from utils import log
from config import BUTTON_PIN, DEBOUNCE_DELAY
import time


class ButtonHandler:
    def __init__(self, on_press):
        self.button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
        self.on_press = on_press
        self.last_button_state = self.button.value()
        log("Button initialized on GPIO {}".format(BUTTON_PIN))

    def handle_button(self) -> None:
        button_state = self.button.value()

        if button_state != self.last_button_state:
            log("Button state changed from {} to {}".format(self.last_button_state, button_state))
            if button_state == 0:
                self.on_press()
            self.last_button_state = button_state
            time.sleep(DEBOUNCE_DELAY)
