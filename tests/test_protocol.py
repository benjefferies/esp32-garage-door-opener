import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "gateway"))

from protocol import parse_ack, parse_state, is_toggle_command


class ParseAckTests(unittest.TestCase):
    def test_parses_id_only(self):
        # given an ack with only a message id
        # when it is parsed
        msg_id, state = parse_ack(b"ack:12")
        # then the id is returned and state is empty
        self.assertEqual(msg_id, 12)
        self.assertIsNone(state)

    def test_parses_id_and_reed_state(self):
        # given an ack that includes reed state
        # when it is parsed
        msg_id, state = parse_ack(b"ack:3:closed")
        # then both id and state are returned
        self.assertEqual(msg_id, 3)
        self.assertEqual(state, "closed")

    def test_rejects_non_ack(self):
        # given a payload that is not an ack
        # when it is parsed
        msg_id, state = parse_ack(b"toggle:1")
        # then nothing is returned
        self.assertIsNone(msg_id)
        self.assertIsNone(state)


class ParseStateTests(unittest.TestCase):
    def test_parses_open_and_closed(self):
        # given state payloads from the opener
        # when they are parsed
        # then the reed name is returned
        self.assertEqual(parse_state(b"state:open"), "open")
        self.assertEqual(parse_state(b"state:closed"), "closed")

    def test_rejects_unknown_state(self):
        # given an unknown state value
        # when it is parsed
        # then it is ignored
        self.assertIsNone(parse_state(b"state:ajar"))


class ToggleCommandTests(unittest.TestCase):
    def test_accepts_common_payloads(self):
        # given MQTT command payloads
        # when they are checked
        # then toggle-like values are accepted
        self.assertTrue(is_toggle_command(b"toggle"))
        self.assertTrue(is_toggle_command(b"toggle:9"))
        self.assertTrue(is_toggle_command(b"OPEN"))
        self.assertFalse(is_toggle_command(b"status"))


if __name__ == "__main__":
    unittest.main()
