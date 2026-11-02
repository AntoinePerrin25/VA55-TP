#!/usr/bin/env python3
"""Robots sur le huit. Le feu suit l'occupation du croisement.

Chaque robot mesure l'arc jusqu'à celui qui le précède. Il ne franchit pas
la distance de suivi, même si sa consigne est plus élevée.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import paho.mqtt.client as mqtt

from circuit import CRUISE_MM_S, load_circuit

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

    @property
    def lane(self) -> str:
        return self.robot_id

    def advance(self, dt: float, may_enter: bool, speed_cap: float, max_step: float) -> None:
        step = min(max(0.0, speed_cap) * dt, max(0.0, max_step))
        gate = self.loop.next_gate(self.s)
        if not may_enter and self.s <= gate.stop_s:
            gap = (gate.stop_s - self.s) % self.loop.length
            if gap <= step:
                self.s = gate.stop_s
                self.speed = 0.0
                return
        if not may_enter and gate.stop_s < self.s < gate.entry_s:
            self.speed = 0.0
            return
        self.s += step
        if self.s >= self.loop.length:
            self.s %= self.loop.length
            self.lap += 1
        self.speed = step / dt if dt else 0.0

    def snapshot(self) -> dict:
        x, y, heading = self.loop.pose(self.s)
        zone = self.loop.zone(self.s)
        return {
            "id": self.robot_id,
            "lane": self.loop.lane,
            "name": self.loop.name,
            "x_mm": round(x, 1),
            "y_mm": round(y, 1),
            "heading_deg": round(heading, 1),
            "speed_mm_s": round(self.speed, 1),
            "zone": zone,
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


def _step(robots: list[Robot], dt: float) -> None:
    """Le plus proche du croisement bouge en premier. Le capteur limite le pas vers l'avant."""
    plans = []
    for robot in robots:
        leader, gap = _ahead(robot, robots)
        robot.sensor_mm = gap if leader is not None and gap <= SENSOR_RANGE_MM else None
        robot.leader_id = leader.robot_id if robot.sensor_mm is not None else None
        room = robot.loop.length if leader is None else max(0.0, gap - FOLLOW_GAP_MM)
        plans.append((robot, _speed_cap(robot, leader, gap), room))
    ordered = sorted(plans, key=lambda item: item[0].loop.distance_to_conflict(item[0].s))
    for robot, cap, room in ordered:
        occupied = any(
            other is not robot and other.loop.zone(other.s) == "conflit" for other in robots
        )
        robot.advance(dt, may_enter=not occupied, speed_cap=cap, max_step=room)


def self_check() -> None:
    circuit = load_circuit(CSV_PATH)
    track = circuit.loops[0]
    gate = track.gates[0]
    waiting = Robot("A", track, gate.stop_s - 40.0)
    inside = Robot("B", track, (gate.entry_s + gate.exit_s) / 2.0)
    for _ in range(8):
        _step([waiting, inside], TICK_S)
    if waiting.speed != 0.0 or waiting.s > gate.stop_s:
        raise RuntimeError("A avance alors que B est dans le croisement")
    inside.s = gate.storage_exit_s + 40.0
    _step([waiting, inside], TICK_S)
    if waiting.speed <= 0.0:
        raise RuntimeError("A reste arrêté alors que le croisement est libre")

    cruise = [
        Robot("A", track, 0.0),
        Robot("B", track, track.length / 2.0),
    ]
    held_while_empty = 0
    for _ in range(int(60.0 / TICK_S)):
        _step(cruise, TICK_S)
        zones = [robot.loop.zone(robot.s) for robot in cruise]
        if zones.count("conflit") > 1:
            raise RuntimeError("les deux robots sont dans le croisement")
        if "conflit" not in zones:
            held_while_empty += sum(robot.speed == 0.0 for robot in cruise)
    if held_while_empty:
        raise RuntimeError(f"arrêt alors que le croisement est vide: {held_while_empty} pas")

    leader = Robot("A", track, 2500.0, cruise=100.0)
    chaser = Robot("B", track, 2500.0 - 450.0, cruise=320.0)
    smallest = track.length
    for _ in range(int(8.0 / TICK_S)):
        _step([leader, chaser], TICK_S)
        gap = (leader.s - chaser.s) % track.length
        smallest = min(smallest, gap)
    if smallest < FOLLOW_GAP_MM - 1.0:
        raise RuntimeError(f"le suiveur entre dans la garde: {smallest:.0f} mm")
    gap = (leader.s - chaser.s) % track.length
    if gap > FOLLOW_GAP_MM + 40.0 or chaser.speed > leader.speed + 30.0:
        raise RuntimeError(
            f"le plus rapide ne s'aligne pas: écart {gap:.0f} mm, "
            f"{chaser.speed:.0f} contre {leader.speed:.0f} mm/s"
        )

    parked = Robot("A", track, 2000.0, cruise=0.0)
    behind = Robot("B", track, 2000.0 - 600.0, cruise=250.0)
    for _ in range(int(8.0 / TICK_S)):
        _step([parked, behind], TICK_S)
    gap = (parked.s - behind.s) % track.length
    if gap < FOLLOW_GAP_MM - 1.0 or behind.speed > 5.0 or abs(parked.s - 2000.0) > 1.0:
        raise RuntimeError(
            f"le suiveur pousse un robot arrêté: écart {gap:.0f} mm, vitesse {behind.speed:.0f}"
        )


class Scene:
    def __init__(self, circuit):
        self.circuit = circuit
        track = circuit.loops[0]
        self.robots = [
            Robot("A", track, 0.0),
            Robot("B", track, track.length / 2.0),
        ]
        self.phase = {
            "phase": "open",
            "green": ["A", "B"],
            "all_red": False,
            "occupied_by": None,
        }
        self.lock = threading.Lock()
        self.started = time.monotonic()

    def set_phase(self, payload: dict) -> None:
        # Le droit de passage affiché est recalculé dans tick à partir des zones.
        # Un feu minuté retenu sur le broker ne doit pas figer un robot hors du disque.
        return

    def tick(self, dt: float) -> list[dict]:
        with self.lock:
            _step(self.robots, dt)
            robots = [robot.snapshot() for robot in self.robots]
            inside = [robot["id"] for robot in robots if robot["zone"] == "conflit"]
            if inside:
                self.phase = {
                    "phase": "occupied",
                    "green": inside,
                    "all_red": False,
                    "occupied_by": inside[0],
                }
            else:
                self.phase = {
                    "phase": "open",
                    "green": [robot["id"] for robot in robots],
                    "all_red": False,
                    "occupied_by": None,
                }
            return robots

    def add_robot(self, cruise: float) -> dict:
        if not MIN_CRUISE_MM_S <= cruise <= MAX_CRUISE_MM_S:
            raise ValueError(
                f"vitesse entre {MIN_CRUISE_MM_S:.0f} et {MAX_CRUISE_MM_S:.0f} mm/s"
            )
        with self.lock:
            track = self.circuit.loops[0]
            position = _spawn_s(self.robots, track.length)
            if position is None:
                raise RuntimeError("plus de place sur le huit")
            robot = Robot(_next_id(self.robots), track, position, cruise)
            self.robots.append(robot)
            return robot.snapshot()

    def document(self, robots: list[dict]) -> dict:
        with self.lock:
            phase = dict(self.phase)
        return {
            "time_s": round(time.monotonic() - self.started, 2),
            "phase": phase,
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


def _spawn_s(robots: list[Robot], length: float) -> float | None:
    if not robots:
        return 0.0
    positions = sorted(robot.s % length for robot in robots)
    best_gap = -1.0
    best_s = 0.0
    for index, position in enumerate(positions):
        nxt = positions[(index + 1) % len(positions)]
        gap = (nxt - position) % length
        if gap == 0.0:
            gap = length
        if gap > best_gap:
            best_gap = gap
            best_s = position
    if best_gap < FOLLOW_GAP_MM * 2.0 + 40.0:
        return None
    return (best_s + best_gap / 2.0) % length


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


def listen(scene: Scene) -> mqtt.Client:
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="sim-huit",
        protocol=mqtt.MQTTv311,
    )

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code != 0:
            print(f"MQTT refusé: {reason_code}")
            return
        client.subscribe(PHASE_TOPIC, qos=1)

    def on_message(client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except json.JSONDecodeError:
            print("phase illisible:", message.payload)
            return
        if isinstance(payload, dict) and "phase" in payload:
            scene.set_phase(payload)

    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=5)
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
    client.loop_start()
    return client


def main() -> None:
    self_check()
    circuit = load_circuit(CSV_PATH)
    scene = Scene(circuit)
    latest = {"doc": scene.document([robot.snapshot() for robot in scene.robots])}
    serve(scene, latest)
    client = listen(scene)
    print(f"vue http://127.0.0.1:{HTTP_PORT}  broker {BROKER_HOST}:{BROKER_PORT}")
    published = 0.0
    try:
        while True:
            robots = scene.tick(TICK_S)
            latest["doc"] = scene.document(robots)
            published += TICK_S
            if published >= PUBLISH_S:
                published = 0.0
                for robot in robots:
                    client.publish(
                        f"robots/{robot['id']}/state",
                        json.dumps(robot),
                        qos=0,
                        retain=False,
                    )
            time.sleep(TICK_S)
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
