import json
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gateway"))

from button_handler import held_long_enough
from provision import captive_payload, captive_probe, dns_reply, form_page, need_sw1_page, parse_body, parse_form_body, parse_request_target, portal_home_page, saved_page, url_unquote, wifi_fields
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

    def test_captive_probes_open_the_garage_sheet(self):
        # given phone captive-portal checks
        # when they hit the setup AP
        # then they get the Garage sheet instead of a Success dismiss
        self.assertTrue(captive_probe("/generate_204"))
        self.assertTrue(captive_probe("/hotspot-detect.html"))
        self.assertFalse(captive_probe("/api/status"))
        html = captive_payload("/", "CaptiveNetworkSupport-386.0.1 wispr")[0]
        self.assertIn("Press the pair button", html)
        self.assertIn("garage-gw connected", html)
        self.assertIn("Processing", html)
        self.assertIsNone(captive_payload("/", "Mozilla/5.0"))

    def test_saved_page_shows_joining_home_wifi(self):
        # given Wi-Fi credentials were posted from the form
        # when the saved page is rendered
        # then it looks like the app and says the SoftAP will close
        html = saved_page()
        self.assertIn("Connecting to home Wi-Fi", html)
        self.assertIn("setup network will close", html)
        self.assertIn("Join home Wi-Fi", html)
        self.assertIn("Processing", html)
        self.assertIn("#setup?saved=1", html)
        self.assertIn("Open the Garage app", html)
        self.assertNotIn("__APP__", html)
        self.assertNotIn("__ORIGIN__", html)

    def test_portal_home_continues_after_sw1(self):
        # given the phone opened the captive sheet
        # when the portal home page is rendered
        # then SW1 sends the browser to the Wi-Fi form
        html = portal_home_page()
        self.assertIn("Press the pair button", html)
        self.assertIn("/wifi", html)
        self.assertIn("Continue to Wi-Fi setup", html)
        self.assertIn("Processing", html)
        self.assertIn("Press pair button", html)
        self.assertNotIn("Close this Wi-Fi login sheet", html)

    def test_wifi_form_matches_app_checklist(self):
        # given SW1 already happened
        # when the Wi-Fi form is shown
        # then it keeps the Garage look
        html = form_page("Set the home Wi-Fi", "abc")
        self.assertIn('name="n" value="abc"', html)
        self.assertIn("Home SSID", html)
        self.assertIn("Save and connect", html)

    def test_dns_reply_points_at_softap(self):
        # given a DNS A query on the setup AP
        # when it is answered
        # then the phone is sent to 192.168.4.1
        query = (
            b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
            b"\x01a\x03com\x00\x00\x01\x00\x01"
        )
        reply = dns_reply(query)
        self.assertTrue(reply.startswith(b"\x12\x34\x81\x80"))
        self.assertTrue(reply.endswith(b"\xc0\xa8\x04\x01"))

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

    def test_portal_save_writes_wifi_json(self):
        # given a successful SoftAP Wi-Fi post
        # when credentials are stored immediately
        # then a later reset can still join that network
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "wifi.json")
            save_wifi("cafe", "hidden", pair_nonce="abc", path=path)
            self.assertEqual(load_wifi(path), ("cafe", "hidden"))
            self.assertEqual(peek_pair_nonce(path), "abc")


if __name__ == "__main__":
    unittest.main()
