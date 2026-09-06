"""HiveMQ Cloud MQTT client for the gateway."""

import ssl
import time
from umqtt.simple import MQTTClient, MQTTException
from utils import log
from protocol import is_toggle_command
from config import (
    MQTT_KEEPALIVE_S,
    MQTT_TOPIC_CMD,
    MQTT_TOPIC_STATE,
    MQTT_TOPIC_ACK,
    MQTT_TOPIC_STATUS,
)


class GatewayMqtt:
    def __init__(self, on_toggle):
        self.on_toggle = on_toggle
        self.client = None
        self._last_ping = time.ticks_ms()

    def connect(self) -> bool:
        try:
            from secrets import (
                MQTT_HOST,
                MQTT_PORT,
                MQTT_USER,
                MQTT_PASSWORD,
                MQTT_CLIENT_ID,
            )
        except ImportError:
            log("No secrets.py — MQTT disabled")
            return False

        if not MQTT_HOST or MQTT_HOST.startswith("xxxx"):
            log("MQTT_HOST not set — MQTT disabled")
            return False

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.verify_mode = ssl.CERT_NONE

        client = MQTTClient(
            MQTT_CLIENT_ID,
            MQTT_HOST,
            port=MQTT_PORT,
            user=MQTT_USER,
            password=MQTT_PASSWORD,
            keepalive=MQTT_KEEPALIVE_S,
            ssl=ctx,
        )
        client.set_callback(self._on_message)

        last_err = None
        for attempt in range(1, 4):
            try:
                log("Connecting MQTT {}:{} ({})".format(MQTT_HOST, MQTT_PORT, attempt))
                client.connect()
                client.subscribe(MQTT_TOPIC_CMD)
                self.client = client
                self._last_ping = time.ticks_ms()
                log("MQTT subscribed to {}".format(MQTT_TOPIC_CMD))
                try:
                    client.publish(MQTT_TOPIC_STATUS, b"online", retain=True)
                except (OSError, MQTTException, AssertionError):
                    log("MQTT status publish skipped (subscribe-only user)")
                return True
            except (OSError, MQTTException, AssertionError) as err:
                last_err = err
                log("MQTT connect failed: {}".format(err))
                time.sleep_ms(1000)
        self.client = None
        log("MQTT gave up: {}".format(last_err))
        return False

    def _on_message(self, topic, msg):
        log("MQTT {} {}".format(topic, msg))
        if topic == MQTT_TOPIC_CMD.encode() and is_toggle_command(msg):
            self.on_toggle()

    def check(self) -> None:
        if not self.client:
            return
        try:
            self.client.check_msg()
            if time.ticks_diff(time.ticks_ms(), self._last_ping) > (MQTT_KEEPALIVE_S * 1000) // 2:
                self.client.ping()
                self._last_ping = time.ticks_ms()
        except OSError as err:
            if err.args and err.args[0] in (-1, 11, 110, 116):
                return
            log("MQTT error, reconnecting: {}".format(err))
            self.connect()

    def publish_state(self, state) -> None:
        self._publish(MQTT_TOPIC_STATE, state.encode(), retain=True)

    def publish_ack(self, msg_id) -> None:
        self._publish(MQTT_TOPIC_ACK, ("ack:%s" % msg_id).encode())

    def _publish(self, topic, msg, retain=False) -> None:
        if not self.client:
            return
        try:
            self.client.publish(topic, msg, retain=retain)
        except OSError as err:
            log("MQTT publish failed: {}".format(err))
