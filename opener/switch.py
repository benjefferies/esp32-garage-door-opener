"""
Switch controller for the garage door opener
"""

from machine import Pin
from settings import OCTOCUPLER_PIN, GARAGE_DOOR_PULSE_MS
import time


class SwitchController:
    def __init__(self, is_cold_boot=False):
        self.is_cold_boot = is_cold_boot
        self.switch = None
        self.initialize()

    def initialize(self):
        self.switch = Pin(OCTOCUPLER_PIN, Pin.OUT, value=0)
        if self.is_cold_boot:
            print("Switch initialized on GPIO {}".format(OCTOCUPLER_PIN))

    def toggle(self):
        if not self.switch:
            return False

        print("Toggling switch...")
        self.switch.value(1)
        time.sleep_ms(GARAGE_DOOR_PULSE_MS)
        self.switch.value(0)
        return True

    def get_state(self):
        return self.switch.value() if self.switch else 0

    def cleanup(self):
        if self.switch:
            self.switch.value(0)
            self.switch = None
