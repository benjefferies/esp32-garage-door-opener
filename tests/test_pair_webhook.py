import sys
import unittest
from pathlib import Path
from types import ModuleType
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gateway"))

import pair_webhook


class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.closed = False

    def close(self):
        self.closed = True


class PairWebhookTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.status_code = 200

        secrets = ModuleType("secrets")
        secrets.CONVEX_SITE_URL = "https://example.convex.site/"
        secrets.DOOR_WEBHOOK_SECRET = "test-secret"
        self.secrets = secrets

        urequests = ModuleType("urequests")

        def post(url, json=None, headers=None):
            self.calls.append({"url": url, "json": json, "headers": headers})
            return FakeResponse(self.status_code)

        urequests.post = post
        self.urequests = urequests

    def _install_modules(self):
        sys.modules["secrets"] = self.secrets
        sys.modules["urequests"] = self.urequests

    def tearDown(self):
        sys.modules.pop("secrets", None)
        sys.modules.pop("urequests", None)

    def test_posts_door_state_to_convex(self):
        # given Convex webhook settings on the gateway
        self._install_modules()

        # when reed state is published
        ok = pair_webhook.post_door_state("closed")

        # then Convex receives the state on /api/door-state
        self.assertTrue(ok)
        self.assertEqual(
            self.calls,
            [
                {
                    "url": "https://example.convex.site/api/door-state",
                    "json": {"state": "closed", "gatewayOnline": True},
                    "headers": {"Authorization": "Bearer test-secret"},
                }
            ],
        )

    def test_posts_heartbeat_without_state(self):
        # given Convex webhook settings on the gateway
        self._install_modules()

        # when a heartbeat is due
        ok = pair_webhook.post_heartbeat()

        # then Convex is told the gateway is online
        self.assertTrue(ok)
        self.assertEqual(self.calls[0]["json"], {"gatewayOnline": True})

    def test_posts_pair_confirmation(self):
        # given Convex webhook settings on the gateway
        self._install_modules()

        # when SW1 confirms pairing
        ok = pair_webhook.post_pair_confirmation("abc123")

        # then Convex receives the nonce on /api/pair
        self.assertTrue(ok)
        self.assertEqual(
            self.calls[0],
            {
                "url": "https://example.convex.site/api/pair",
                "json": {"nonce": "abc123"},
                "headers": {"Authorization": "Bearer test-secret"},
            },
        )

    def test_skips_when_secrets_missing(self):
        # given no Convex settings on the device
        sys.modules.pop("secrets", None)
        sys.modules["urequests"] = self.urequests

        # when a door update is attempted
        ok = pair_webhook.post_door_state("open")

        # then nothing is posted
        self.assertFalse(ok)
        self.assertEqual(self.calls, [])

    def test_returns_false_on_http_error(self):
        # given Convex rejects the webhook
        self.status_code = 401
        self._install_modules()

        # when a heartbeat is posted
        ok = pair_webhook.post_heartbeat()

        # then the caller is told it failed
        self.assertFalse(ok)

    def test_returns_false_when_request_raises(self):
        # given HTTPS is unavailable
        self._install_modules()

        def boom(*_args, **_kwargs):
            raise OSError("tls fail")

        self.urequests.post = boom

        # when a pair confirm is attempted
        ok = pair_webhook.post_pair_confirmation("n")

        # then the error is swallowed
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
