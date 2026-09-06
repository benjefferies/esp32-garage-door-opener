import json
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gateway"))

from button_handler import held_long_enough
from provision import parse_form_body, url_unquote
from wifi_store import clear_wifi, load_wifi, save_wifi


class FormParseTests(unittest.TestCase):
    def test_unquotes_spaces_and_symbols(self):
        # given a form-encoded password
        # when it is decoded
        # then plus and percent escapes are restored
        self.assertEqual(url_unquote("Google+Wifi"), "Google Wifi")
        self.assertEqual(url_unquote("a%40b"), "a@b")

    def test_parses_ssid_and_password(self):
        # given a POST body
        # when it is parsed
        # then both fields are returned
        fields = parse_form_body(b"ssid=home-net&password=s3cret")
        self.assertEqual(fields["ssid"], "home-net")
        self.assertEqual(fields["password"], "s3cret")


class HoldResetTests(unittest.TestCase):
    def test_three_seconds_is_a_reset(self):
        # given a 3s hold threshold
        # when SW1 is held
        # then only presses at or past 3s count as reset
        self.assertFalse(held_long_enough(2999, threshold_s=3))
        self.assertTrue(held_long_enough(3000, threshold_s=3))


class WifiStoreTests(unittest.TestCase):
    def test_round_trip(self):
        # given credentials written to flash
        # when they are loaded
        # then the same ssid is returned
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "wifi.json")
            save_wifi("cafe", "hidden", path=path)
            ssid, password = load_wifi(path)
            self.assertEqual(ssid, "cafe")
            self.assertEqual(password, "hidden")
            data = json.loads(Path(path).read_text())
            self.assertEqual(data["ssid"], "cafe")
            clear_wifi(path)
            self.assertEqual(load_wifi(path), (None, None))


if __name__ == "__main__":
    unittest.main()
