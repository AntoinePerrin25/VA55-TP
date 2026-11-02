#!/usr/bin/env pybricks-micropython

import _thread

from pybricks.tools import wait

from capteur_distance import CapteurDistance
from intersection import (
    distance_to_crossing,
    speed_command,
)


class RobotIntersection(object):
    """Publie l'état Kalman et applique le feu plus le capteur de distance."""

    def __init__(self, robot, robot_id, broker, port=1883):
        self.robot = robot
        self.robot_id = robot_id
        self.broker = broker
        self.port = port
        self._phase = None
        self._clearing = False
        self._run = True
        self._client = None
        self._connected = False
        self._outgoing = None
        self._topic = "robots/{0}/state".format(robot_id)
        self._screen_ms = 0
        self._range = None
        try:
            self._range = CapteurDistance()
        except Exception:
            self._range = None
        self.robot.own_screen = True
        _thread.start_new_thread(self._comm, ())

    def limit(self, speed):
        pose = self.robot.poses.get("kalman") or (0.0, 0.0, 0.0)
        dist = distance_to_crossing(pose[0], pose[1])
        sensor = None
        if self._range is not None:
            sensor = self._range.distance()
        limited, zone, self._clearing = speed_command(
            speed, dist, self._clearing, self._phase, self.robot_id, sensor
        )
        self._outgoing = _encode({
            "id": self.robot_id,
            "lane": "huit",
            "x_mm": round(pose[0], 1),
            "y_mm": round(pose[1], 1),
            "heading_deg": round(pose[2], 1),
            "speed_mm_s": round(limited, 1),
            "zone": zone,
            "distance_to_conflict_mm": round(max(0.0, dist - 220.0), 1),
            "sensor_mm": None if sensor is None else int(sensor),
            "leader_id": None,
        })
        self._screen(zone, limited, sensor)
        return limited

    def close(self):
        self._run = False

    def _screen(self, zone, speed, sensor):
        now = self.robot.watch.time()
        if now - self._screen_ms < 200:
            return
        self._screen_ms = now
        if zone == "conflit":
            light = "conflit"
        elif sensor is not None and sensor <= 280:
            light = "suivi"
        elif zone == "stockage" and speed == 0:
            light = "rouge"
        elif self._connected:
            light = "libre"
        else:
            light = "sans mqtt"
        if sensor is None:
            second = "capteur --"
        else:
            second = "capteur {0}".format(int(sensor))
        self.robot.updateLCD("{0} {1}\n{2}".format(self.robot_id, light, second))

    def _connect(self):
        try:
            from umqtt.robust import MQTTClient
        except ImportError:
            from umqtt.simple import MQTTClient
        try:
            client = MQTTClient(self.robot_id, self.broker, port=self.port)
            client.set_callback(self._on_message)
            client.connect()
            client.subscribe("intersection/phase")
        except Exception:
            self._client = None
            self._connected = False
            return
        self._client = client
        self._connected = True

    def _on_message(self, topic, msg):
        try:
            import ujson as json
        except ImportError:
            import json
        if not isinstance(msg, str):
            msg = msg.decode("utf-8")
        try:
            payload = json.loads(msg)
        except Exception:
            return
        if isinstance(payload, dict) and "phase" in payload:
            self._phase = payload

    def _comm(self):
        while self._run:
            if self._client is None:
                self._connect()
                wait(500)
                continue
            payload = self._outgoing
            self._outgoing = None
            try:
                if payload is not None:
                    self._client.publish(self._topic, payload)
                self._client.check_msg()
            except Exception:
                self._client = None
                self._connected = False
            wait(50)


def _encode(payload):
    try:
        import ujson as json
    except ImportError:
        import json
    text = json.dumps(payload)
    if isinstance(text, str):
        return text.encode("utf-8")
    return text
