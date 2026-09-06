import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gateway"))

if not hasattr(time, "ticks_ms"):
    time.ticks_ms = lambda: int(time.time() * 1000)
    time.ticks_diff = lambda a, b: a - b

import button_handler
from button_handler import ButtonHandler


class FakePin:
    def __init__(self, value=1):
        self._value = value

    def value(self):
        return self._value


class FakeClock:
    def __init__(self):
        self.now = 0

    def ticks_ms(self):
        return self.now

    def ticks_diff(self, a, b):
        return a - b


class BootHeldTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.original = button_handler.time
        button_handler.time = self.clock

    def tearDown(self):
        button_handler.time = self.original

    def test_already_down_does_not_wipe_wifi(self):
        # given GPIO9/BOOT is low when the handler starts (USB reset)
        pin = FakePin(0)
        wiped = []
        handler = ButtonHandler(on_press=lambda: None, on_long_press=lambda: wiped.append(True), pin=pin)

        # when 4s pass while it stays down
        self.clock.now = 4000
        handler.handle_button()

        # then wifi is not forgotten
        self.assertEqual(wiped, [])

    def test_release_then_hold_still_resets(self):
        # given BOOT was held at start
        pin = FakePin(0)
        wiped = []
        handler = ButtonHandler(on_press=lambda: None, on_long_press=lambda: wiped.append(True), pin=pin)
        pin._value = 1
        handler.handle_button()

        # when the user presses again and holds 3s
        pin._value = 0
        handler.handle_button()
        self.clock.now = 3000
        handler.handle_button()

        # then the 3s hold still forgets Wi-Fi
        self.assertEqual(wiped, [True])
