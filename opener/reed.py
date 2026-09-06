"""Reed switch on GPIO3. Magnet present (CLOSED) shorts the pin to GND."""

from machine import Pin, RTC
from settings import REED_PIN


class ReedSensor:
    def __init__(self):
        self.pin = Pin(REED_PIN, Pin.IN, Pin.PULL_UP)
        self.rtc = RTC()

    def read_name(self):
        return "closed" if self.pin.value() == 0 else "open"

    def take_if_changed(self):
        """Return open/closed when it differs from the last value stored in RTC."""
        current = self.read_name()
        last = bytes(self.rtc.memory())
        if last == current.encode():
            return None
        self.rtc.memory(current.encode())
        return current
