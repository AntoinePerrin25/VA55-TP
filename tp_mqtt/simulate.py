#!/usr/bin/env python3
"""Simule le huit ou affiche la télémétrie des EV3 sur le même plan."""

from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import paho.mqtt.client as mqtt

from circuit import CRUISE_MM_S, STOP_RADIUS_MM, load_circuit

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT.parent / "trajectoire_2.csv"
BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883
PHASE_TOPIC = "intersection/phase"
HTTP_PORT = 8765
TICK_S = 0.05
PUBLISH_S = 0.1
FOLLOW_GAP_MM = 280.0
SENSOR_RANGE_MM = 800.0
MIN_CRUISE_MM_S = 40.0
MAX_CRUISE_MM_S = 500.0
REQUEST_BEFORE_STOP_MM = 160.0
PHASE_TIMEOUT_S = 0.75


class Robot:
    def __init__(self, robot_id: str, loop, s: float, cruise: float = CRUISE_MM_S):
        self.robot_id = robot_id
        self.loop = loop
        self.s = s % loop.length
        self.cruise = cruise
        self.speed = cruise
        self.lap = 1
        self.sensor_mm = None
        self.leader_id = None
        self.passage = "ligne"

    def distance_to_stop(self) -> float:
        return (self.loop.next_gate(self.s).stop_s - self.s) % self.loop.length

    def advance(self, dt: float, permitted: bool, speed_cap: float, max_step: float) -> None:
        step = min(speed_cap * dt, max_step)
        gate = self.loop.next_gate(self.s)
        if self.passage == "engage":
            if self.s + step >= gate.clear_s:
                self.passage = "libere"
        elif self.distance_to_stop() <= step:
            if permitted:
                self.passage = "engage"
            else:
                step = self.distance_to_stop()
        self.s += step
        if self.s >= self.loop.length:
            self.s %= self.loop.length
            self.lap += 1
        self.speed = step / dt

    def snapshot(self) -> dict:
        x, y, heading = self.loop.pose(self.s)
        zone = self.loop.zone(self.s)
        passage = self.passage
        if passage != "engage" and self.distance_to_stop() <= REQUEST_BEFORE_STOP_MM:
            passage = "approche"
        return {
            "id": self.robot_id,
            "lane": self.loop.lane,
            "name": self.loop.name,
            "x_mm": round(x, 1),
            "y_mm": round(y, 1),
            "heading_deg": round(heading, 1),
            "speed_mm_s": round(self.speed, 1),
            "zone": zone,
            "passage": passage,
            "distance_to_conflict_mm": round(self.loop.distance_to_conflict(self.s), 1),
            "progress_mm": round(self.s, 1),
            "lap": self.lap,
            "cruise_mm_s": round(self.cruise, 1),
            "sensor_mm": None if self.sensor_mm is None else round(self.sensor_mm, 1),
            "leader_id": self.leader_id,
        }


def _ahead(robot: Robot, robots: list[Robot]) -> tuple[Robot | None, float]:
    leader = None
    gap = robot.loop.length
    for other in robots:
        if other is robot:
            continue
        distance = (other.s - robot.s) % robot.loop.length
        if distance < gap:
            gap = distance
            leader = other
    return leader, gap


def _speed_cap(robot: Robot, leader: Robot | None, gap: float) -> float:
    if leader is None or gap >= SENSOR_RANGE_MM:
        return robot.cruise
    if gap <= FOLLOW_GAP_MM:
        return min(robot.cruise, leader.speed)
    blend = (gap - FOLLOW_GAP_MM) / (SENSOR_RANGE_MM - FOLLOW_GAP_MM)
    capped = leader.speed + blend * (robot.cruise - leader.speed)
    return max(0.0, min(robot.cruise, capped))


def _step(robots: list[Robot], dt: float, green: list[str]) -> None:
    plans = []
    for robot in robots:
        leader, gap = _ahead(robot, robots)
        robot.sensor_mm = gap if leader is not None and gap <= SENSOR_RANGE_MM else None
        robot.leader_id = leader.robot_id if robot.sensor_mm is not None else None
        room = robot.loop.length if leader is None else max(0.0, gap - FOLLOW_GAP_MM)
        plans.append((robot, _speed_cap(robot, leader, gap), room))
    for robot, cap, room in plans:
        robot.advance(dt, robot.robot_id in green, cap, room)


class Scene:
    def __init__(self, circuit, observe: bool):
        self.circuit = circuit
        self.observe = observe
        track = circuit.loops[0]
        self.robots = [] if observe else [
            Robot("A", track, 0.0),
            Robot("B", track, track.length / 2.0),
        ]
        self.phase = None
        self.phase_at = 0.0
        self.telemetry = {}
        self.lock = threading.Lock()
        self.started = time.monotonic()

    def set_phase(self, payload: dict | None) -> None:
        with self.lock:
            self.phase = payload
            self.phase_at = time.monotonic()

    def set_telemetry(self, state: dict) -> None:
        with self.lock:
            self.telemetry[state["id"]] = (time.monotonic(), state)

    def current_phase(self) -> dict | None:
        if time.monotonic() - self.phase_at < PHASE_TIMEOUT_S:
            return self.phase
        return None

    def tick(self, dt: float) -> list[dict]:
        with self.lock:
            if self.observe:
                now = time.monotonic()
                return [state for seen, state in self.telemetry.values() if now - seen < 2.0]
            phase = self.current_phase()
            _step(self.robots, dt, phase["green"] if phase else [])
            return [robot.snapshot() for robot in self.robots]

    def add_robot(self, cruise: float) -> dict:
        if self.observe:
            raise RuntimeError("observation des EV3")
        if not MIN_CRUISE_MM_S <= cruise <= MAX_CRUISE_MM_S:
            raise ValueError(
                f"vitesse entre {MIN_CRUISE_MM_S:.0f} et {MAX_CRUISE_MM_S:.0f} mm/s"
            )
        with self.lock:
            track = self.circuit.loops[0]
            position = _spawn_s(self.robots, track)
            if position is None:
                raise RuntimeError("plus de place sur le huit")
            robot = Robot(_next_id(self.robots), track, position, cruise)
            self.robots.append(robot)
            return robot.snapshot()

    def document(self, robots: list[dict]) -> dict:
        with self.lock:
            phase = self.current_phase()
        return {
            "time_s": round(time.monotonic() - self.started, 2),
            "phase": phase,
            "observe": self.observe,
            "stop_radius_mm": STOP_RADIUS_MM,
            "center": [round(self.circuit.center[0], 1), round(self.circuit.center[1], 1)],
            "conflict_radius_mm": self.circuit.conflict_radius_mm,
            "storage_radius_mm": self.circuit.storage_radius_mm,
            "loops": [
                {
                    "lane": loop.lane,
                    "name": loop.name,
                    "points": [[round(point[0], 1), round(point[1], 1)] for point in loop.points],
                }
                for loop in self.circuit.loops
            ],
            "robots": robots,
        }


def _spawn_s(robots: list[Robot], track) -> float | None:
    positions = sorted(robot.s for robot in robots)
    candidates = []
    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else positions[0] + track.length
        gap = end - start
        if gap < 2 * FOLLOW_GAP_MM + 40:
            continue
        middle = (start + gap / 2) % track.length
        gate = track.next_gate(middle)
        if gate.stop_s <= middle <= gate.storage_exit_s:
            continue
        candidates.append((gap, middle))
    return max(candidates)[1] if candidates else None


def _next_id(robots: list[Robot]) -> str:
    used = {robot.robot_id for robot in robots}
    for code in range(ord("A"), ord("Z") + 1):
        name = chr(code)
        if name not in used:
            return name
    raise RuntimeError("vingt-six robots déjà sur le circuit")


def serve(scene: Scene, latest: dict) -> None:
    page = (ROOT / "view.html").read_text(encoding="utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/scene"):
                body = json.dumps(latest["doc"]).encode("utf-8")
                self._send(200, "application/json", body)
                return
            if self.path in ("/", "/index.html"):
                self._send(200, "text/html; charset=utf-8", page.encode("utf-8"))
                return
            self._send(404, "text/plain", b"not found")

        def do_POST(self):
            path = self.path.split("?", 1)[0]
            if path != "/robots":
                self._send(404, "application/json", b'{"error":"not found"}')
                return
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    raise ValueError("objet JSON attendu")
                cruise = float(payload.get("speed_mm_s", 280))
                robot = scene.add_robot(cruise)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                message = exc.args[0] if exc.args else "requête illisible"
                self._send(400, "application/json", json.dumps({"error": str(message)}).encode("utf-8"))
                return
            except RuntimeError as exc:
                self._send(409, "application/json", json.dumps({"error": str(exc)}).encode("utf-8"))
                return
            self._send(201, "application/json", json.dumps(robot).encode("utf-8"))

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", HTTP_PORT), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()


def listen(scene: Scene, broker: str, port: int) -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            print(f"MQTT refusé: {reason_code}")
            return
        client.subscribe(PHASE_TOPIC, qos=1)
        if scene.observe:
            client.subscribe("robots/+/state", qos=0)

    def on_disconnect(client, userdata, flags, reason_code, properties):
        scene.set_phase(None)

    def on_message(client, userdata, message):
        if message.retain:
            return
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeError, ValueError):
            return
        if not isinstance(payload, dict):
            return
        if message.topic == PHASE_TOPIC:
            green = payload.get("green")
            if payload.get("mode") == "acces_cooperatif" and isinstance(green, list) and len(green) <= 1:
                scene.set_phase(payload)
        elif scene.observe and payload.get("id"):
            pose = ("x_mm", "y_mm", "heading_deg")
            if all(isinstance(payload.get(key), (int, float)) for key in pose):
                scene.set_telemetry(payload)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=5)
    client.connect(broker, port, keepalive=15)
    client.loop_start()
    return client


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--broker", default=BROKER_HOST)
    parser.add_argument("--port", type=int, default=BROKER_PORT)
    parser.add_argument("--observe", action="store_true", help="afficher les EV3 sans simuler de robots")
    args = parser.parse_args()
    scene = Scene(load_circuit(CSV_PATH), args.observe)
    simulation_session = uuid4().hex
    latest = {"doc": scene.document(scene.tick(TICK_S))}
    client = listen(scene, args.broker, args.port)
    print(f"Vue http://127.0.0.1:{HTTP_PORT} · MQTT {args.broker}:{args.port}", flush=True)
    try:
        serve(scene, latest)
        published = 0.0
        while True:
            robots = scene.tick(TICK_S)
            latest["doc"] = scene.document(robots)
            published += TICK_S
            if not args.observe and published >= PUBLISH_S:
                published = 0.0
                for robot in robots:
                    state = dict(robot, simulation_session=simulation_session)
                    client.publish(f"robots/{robot['id']}/state", json.dumps(state), qos=0)
            time.sleep(TICK_S)
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
