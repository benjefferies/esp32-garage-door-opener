import json
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gateway"))

from button_handler import held_long_enough
from provision import captive_probe, need_sw1_page, parse_body, parse_form_body, parse_request_target, url_unquote, wifi_fields
from wifi_store import clear_pair_nonce, clear_wifi, load_wifi, peek_pair_nonce, save_wifi


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

    def test_parses_request_target_and_json_body(self):
        # given an API request from the cached web app
        # when the path and JSON body are parsed
        # then the nonce is available for SoftAP pairing
        method, path, query = parse_request_target("GET /api/status?n=abc123 HTTP/1.0")
        self.assertEqual(method, "GET")
        self.assertEqual(path, "/api/status")
        self.assertEqual(query["n"], "abc123")
        fields = parse_body(b'{"ssid":"cafe","password":"x","nonce":"deadbeef"}', "application/json")
        self.assertEqual(wifi_fields(fields), ("cafe", "x", "deadbeef"))
        form = parse_body(b"ssid=cafe&password=x&n=deadbeef", "application/x-www-form-urlencoded")
        self.assertEqual(wifi_fields(form), ("cafe", "x", "deadbeef"))

    def test_captive_probes_look_online(self):
        # given phone captive-portal checks
        # when they hit the setup AP
        # then they get a success body so the OS does not steal the Garage tab
        self.assertEqual(captive_probe("/generate_204")[1], "204 No Content")
        self.assertEqual(captive_probe("/hotspot-detect.html")[0], "Success")
        self.assertIsNone(captive_probe("/api/status"))

    def test_need_sw1_page_keeps_credentials(self):
        # given a form post before SW1
        # when the wait page is rendered
        # then the ssid is echoed for a retry
        html = need_sw1_page("abc", 'cafe"net', "x")
        self.assertIn("Press the pair button", html)
        self.assertIn("cafe&quot;net", html)
        self.assertIn('value="abc"', html)


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
            save_wifi("cafe", "hidden", pair_nonce="deadbeef", path=path)
            ssid, password = load_wifi(path)
            self.assertEqual(ssid, "cafe")
            self.assertEqual(password, "hidden")
            self.assertEqual(peek_pair_nonce(path), "deadbeef")
            data = json.loads(Path(path).read_text())
            self.assertEqual(data["ssid"], "cafe")
            self.assertEqual(data["pair_nonce"], "deadbeef")
            clear_pair_nonce(path)
            self.assertEqual(peek_pair_nonce(path), None)
            self.assertEqual(load_wifi(path), ("cafe", "hidden"))
            clear_wifi(path)
            self.assertEqual(load_wifi(path), (None, None))


if __name__ == "__main__":
    unittest.main()
