#!/usr/bin/env pybricks-micropython

import _thread
from math import cos, pi, sin

import ujson
from pybricks.tools import StopWatch, wait
from umqtt.simple import MQTTClient, MQTTException

from capteur_distance import CapteurDistance
from intersection import (
    CONFLICT_RADIUS_MM, PHASE_TIMEOUT_MS, crossing_state,
    distance_to_crossing, speed_command,
)

PHASE_TOPIC = b"intersection/phase"
COMM_PERIOD_MS = 50


class RobotIntersection:
    """Le PID pilote les moteurs. Ce module limite sa vitesse et échange par MQTT."""

    def __init__(self, robot, robot_id, broker, port=1883, start_pose=(0, 0, 0)):
        self.robot = robot
        self.robot_id = robot_id
        self.broker = broker
        self.port = port
        self.start_pose = start_pose
        angle = start_pose[2] * pi / 180
        self.cos_start = cos(angle)
        self.sin_start = sin(angle)
        self.watch = StopWatch()
        self.phase = None
        self.passage = "ligne"
        self.crossed = False
        self.running = True
        self.state = None
        self.state_topic = ("robots/{0}/state".format(robot_id)).encode()
        self.screen_ms = -300
        self.sensor_ms = -COMM_PERIOD_MS
        self.sensor = CapteurDistance()
        self.sensor_mm = None
        self.robot.own_screen = True
        _thread.start_new_thread(self.communicate, ())

    def limit(self, speed):
        x, y, heading = self.robot.poses["kalman"]
        x0, y0, heading0 = self.start_pose
        x, y = (x0 + x * self.cos_start - y * self.sin_start,
                y0 + x * self.sin_start + y * self.cos_start)
        distance = distance_to_crossing(x, y)
        now = self.watch.time()
        phase = self.phase
        fresh = phase is not None and now - phase[0] < PHASE_TIMEOUT_MS
        permitted = fresh and self.robot_id in phase[1]

        if now - self.sensor_ms >= COMM_PERIOD_MS:
            self.sensor_mm = self.sensor.distance()
            self.sensor_ms = now
        zone, self.passage, self.crossed = crossing_state(
            distance, self.passage, self.crossed, permitted)
        limited = speed_command(speed, distance, self.passage, self.sensor_mm)
        self.state = {
            "id": self.robot_id,
            "x_mm": round(x, 1),
            "y_mm": round(y, 1),
            "heading_deg": round(heading + heading0, 1),
            "speed_mm_s": round(limited * pi * self.robot.wheel_diameter / 360, 1),
            "zone": zone,
            "passage": self.passage,
            "distance_to_conflict_mm": round(max(0.0, distance - CONFLICT_RADIUS_MM), 1),
            "sensor_mm": self.sensor_mm,
        }

        if now - self.screen_ms >= 300:
            sensor = "--" if self.sensor_mm is None else str(self.sensor_mm)
            light = self.passage if fresh else "sans MQTT"
            self.robot.updateLCD("{0} {1}\n{2} mm".format(self.robot_id, light, sensor))
            self.screen_ms = now
        return limited

    def close(self):
        self.running = False

    def on_message(self, topic, message):
        try:
            body = ujson.loads(message.decode())
        except ValueError:
            return
        if (topic == PHASE_TOPIC and isinstance(body, dict)
                and body.get("mode") == "acces_cooperatif"
                and isinstance(body.get("green"), list)
                and len(body["green"]) <= 1):
            self.phase = (self.watch.time(), body["green"])

    def communicate(self):
        while self.running:
            client = MQTTClient(self.robot_id.encode(), self.broker,
                                port=self.port, keepalive=15)
            client.set_callback(self.on_message)
            try:
                client.connect()
                client.subscribe(PHASE_TOPIC, qos=1)
                while self.running:
                    state = self.state
                    if state is not None:
                        client.publish(self.state_topic, ujson.dumps(state).encode(), qos=0)
                    client.check_msg()
                    wait(COMM_PERIOD_MS)
            except (OSError, ValueError, MQTTException) as error:
                print("MQTT:", error)
            finally:
                self.phase = None
                try:
                    client.disconnect()
                except (OSError, AttributeError):
                    pass
            if self.running:
                wait(500)
