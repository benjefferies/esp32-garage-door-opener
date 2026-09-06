"""Reed switch on GPIO3. Magnet present (CLOSED) shorts the pin to GND."""

from machine import Pin, RTC
from settings import REED_PIN


class ReedSensor:
    def __init__(self):
        self.pin = Pin(REED_PIN, Pin.IN, Pin.PULL_UP)
        self.rtc = RTC()

    def read_name(self):
        return "closed" if self.pin.value() == 0 else "open"

    def _parse_rtc(self):
        raw = bytes(self.rtc.memory())
        if not raw:
            return None, 0
        try:
            text = raw.decode()
        except UnicodeError:
            return None, 0
        if "," in text:
            state, rest = text.rsplit(",", 1)
            try:
                return state or None, int(rest)
            except ValueError:
                return state or None, 0
        return text, 0

    def snapshot(self):
        """Return (name, changed, wake_count) and persist both in RTC."""
        current = self.read_name()
        last, wakes = self._parse_rtc()
        wakes += 1
        changed = last != current
        self.rtc.memory(("{},{}".format(current, wakes)).encode())
        return current, changed, wakes

    def take_if_changed(self):
        """Return open/closed when it differs from the last value stored in RTC."""
        current, changed, _ = self.snapshot()
        return current if changed else None
