"""Circuit en huit tiré du premier tour de trajectoire_2.csv.

La géométrie suit la commande du tour 1 : elle se referme à 90 mm, alors que
le Kalman de ce même tour reste ouvert de 288 mm. Le filtre reste la
localisation à publier sur le brick ; ici la position simulée est la position
sur cette ligne.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

CONFLICT_RADIUS_MM = 220.0
STORAGE_RADIUS_MM = 480.0
SAMPLE_MM = 20.0
CRUISE_MM_S = 200.0
MIN_CROSSING_GAP = 40


@dataclass(frozen=True)
class Gate:
    stop_s: float
    entry_s: float
    exit_s: float
    storage_exit_s: float


@dataclass(frozen=True)
class Loop:
    lane: str
    name: str
    points: tuple[tuple[float, float, float], ...]
    length: float
    gates: tuple[Gate, ...]

    def pose(self, s: float) -> tuple[float, float, float]:
        s = s % self.length
        pts = self.points
        for index in range(len(pts)):
            start = pts[index]
            end = pts[(index + 1) % len(pts)]
            end_s = end[2] if index + 1 < len(pts) else self.length
            if s <= end_s or index == len(pts) - 1:
                span = end_s - start[2]
                if span <= 1e-6:
                    x, y = start[0], start[1]
                else:
                    blend = (s - start[2]) / span
                    x = start[0] + blend * (end[0] - start[0])
                    y = start[1] + blend * (end[1] - start[1])
                ahead = self._xy((s + 40.0) % self.length)
                heading = math.degrees(math.atan2(ahead[1] - y, ahead[0] - x))
                return x, y, heading
        x, y, _ = pts[0]
        return x, y, 0.0

    def _xy(self, s: float) -> tuple[float, float]:
        pts = self.points
        for index in range(len(pts)):
            start = pts[index]
            end = pts[(index + 1) % len(pts)]
            end_s = end[2] if index + 1 < len(pts) else self.length
            if s <= end_s or index == len(pts) - 1:
                span = end_s - start[2]
                if span <= 1e-6:
                    return start[0], start[1]
                blend = (s - start[2]) / span
                return (
                    start[0] + blend * (end[0] - start[0]),
                    start[1] + blend * (end[1] - start[1]),
                )
        return pts[0][0], pts[0][1]

    def zone(self, s: float) -> str:
        s = s % self.length
        for gate in self.gates:
            if gate.entry_s <= s <= gate.exit_s:
                return "conflit"
            if gate.stop_s < s < gate.entry_s:
                return "stockage"
            if gate.exit_s < s <= gate.storage_exit_s:
                return "sortie"
        return "ligne"

    def distance_to_conflict(self, s: float) -> float:
        s = s % self.length
        for gate in self.gates:
            if gate.entry_s <= s <= gate.exit_s:
                return 0.0
        return min((gate.entry_s - s) % self.length for gate in self.gates)

    def next_gate(self, s: float) -> Gate:
        s = s % self.length
        for gate in self.gates:
            if gate.stop_s <= s <= gate.storage_exit_s:
                return gate
        ahead = [gate for gate in self.gates if gate.stop_s > s]
        if ahead:
            return min(ahead, key=lambda gate: gate.stop_s)
        return min(self.gates, key=lambda gate: gate.stop_s)


@dataclass(frozen=True)
class Circuit:
    center: tuple[float, float]
    loops: tuple[Loop, Loop]
    conflict_radius_mm: float
    storage_radius_mm: float
    cruise_mm_s: float

    def loop(self, lane: str) -> Loop:
        for item in self.loops:
            if item.lane == lane:
                return item
        raise KeyError(lane)


def load_circuit(csv_path: Path, lap: int = 1) -> Circuit:
    raw = _read_command_lap(csv_path, lap)
    if len(raw) < MIN_CROSSING_GAP * 2:
        raise ValueError(f"{csv_path} n'a pas assez de points pour le tour {lap}")
    first, second = _crossing_indices(raw)
    center = (
        (raw[first][0] + raw[second][0]) / 2.0,
        (raw[first][1] + raw[second][1]) / 2.0,
    )
    track = _make_loop("huit", raw, center)
    return Circuit(
        center=center,
        loops=(track,),
        conflict_radius_mm=CONFLICT_RADIUS_MM,
        storage_radius_mm=STORAGE_RADIUS_MM,
        cruise_mm_s=CRUISE_MM_S,
    )


def _read_command_lap(csv_path: Path, lap: int) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    with csv_path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("time_s"):
                continue
            cells = line.split(";")
            if int(float(cells[2])) != lap:
                continue
            points.append((float(cells[7]), float(cells[8])))
    return _dedupe(points)


def _dedupe(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    kept = [points[0]]
    for point in points[1:]:
        if math.hypot(point[0] - kept[-1][0], point[1] - kept[-1][1]) >= 1.0:
            kept.append(point)
    return kept


def _crossing_indices(points: list[tuple[float, float]]) -> tuple[int, int]:
    best = math.inf
    pair = (0, 0)
    for left in range(len(points)):
        for right in range(left + MIN_CROSSING_GAP, len(points)):
            distance = math.hypot(
                points[left][0] - points[right][0],
                points[left][1] - points[right][1],
            )
            if distance < best:
                best = distance
                pair = (left, right)
    if best > 80.0:
        raise ValueError(f"le tour ne se croise pas (écart mini {best:.0f} mm)")
    return pair


def _make_loop(name: str, points: list[tuple[float, float]], center: tuple[float, float]) -> Loop:
    opened = _dedupe(points)
    farthest = max(
        range(len(opened)),
        key=lambda index: math.hypot(
            opened[index][0] - center[0], opened[index][1] - center[1]
        ),
    )
    rotated = opened[farthest:] + opened[:farthest]
    samples, length = _resample_closed(rotated, SAMPLE_MM)
    gates = _mark_gates(samples, length, center)
    return Loop(lane=name, name="huit", points=samples, length=length, gates=gates)


def _resample_closed(
    points: list[tuple[float, float]], step: float
) -> tuple[tuple[tuple[float, float, float], ...], float]:
    sequence = points + [points[0]]
    cursor = sequence[0]
    index = 0
    samples = [(cursor[0], cursor[1], 0.0)]
    traveled = 0.0
    next_mark = step
    while index < len(sequence) - 1:
        end = sequence[index + 1]
        segment = math.hypot(end[0] - cursor[0], end[1] - cursor[1])
        if segment < 1e-6:
            index += 1
            cursor = end
            continue
        if traveled + segment >= next_mark:
            blend = (next_mark - traveled) / segment
            cursor = (
                cursor[0] + blend * (end[0] - cursor[0]),
                cursor[1] + blend * (end[1] - cursor[1]),
            )
            traveled = next_mark
            samples.append((cursor[0], cursor[1], traveled))
            next_mark += step
            continue
        traveled += segment
        index += 1
        cursor = end
    closing = math.hypot(points[0][0] - cursor[0], points[0][1] - cursor[1])
    length = traveled + closing
    if length <= step:
        raise ValueError("boucle trop courte")
    return tuple(samples), length


def _mark_gates(
    samples: tuple[tuple[float, float, float], ...],
    length: float,
    center: tuple[float, float],
) -> tuple[Gate, ...]:
    distance = [
        math.hypot(point[0] - center[0], point[1] - center[1]) for point in samples
    ]
    if distance[0] <= STORAGE_RADIUS_MM or distance[-1] <= STORAGE_RADIUS_MM:
        raise ValueError("le départ du huit est encore dans la zone de stockage")
    runs: list[tuple[int, int]] = []
    start = None
    for index, value in enumerate(distance):
        if value <= CONFLICT_RADIUS_MM:
            if start is None:
                start = index
        elif start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, len(distance) - 1))
    if len(runs) != 2:
        raise ValueError(f"le huit doit traverser le croisement deux fois, pas {len(runs)}")
    gates: list[Gate] = []
    previous = 0
    for entry, exit_index in runs:
        stop = entry
        while stop > previous and distance[stop] < STORAGE_RADIUS_MM:
            stop -= 1
        storage_exit = exit_index
        while (
            storage_exit + 1 < len(distance)
            and distance[storage_exit] < STORAGE_RADIUS_MM
        ):
            storage_exit += 1
        gate = Gate(
            stop_s=samples[stop][2],
            entry_s=samples[entry][2],
            exit_s=samples[exit_index][2],
            storage_exit_s=samples[min(storage_exit, len(samples) - 1)][2],
        )
        if not (0 < gate.stop_s < gate.entry_s < gate.exit_s < gate.storage_exit_s < length):
            raise ValueError(f"passage invalide: {gate}")
        gates.append(gate)
        previous = storage_exit
    return tuple(gates)


def crossing_time_s(loop: Loop, cruise_mm_s: float = CRUISE_MM_S) -> float:
    """Durée, à vitesse de croisière, entre la ligne d'arrêt et la sortie du conflit."""
    gate = loop.gates[0]
    return (gate.exit_s - gate.stop_s) / cruise_mm_s


if __name__ == "__main__":
    circuit = load_circuit(Path(__file__).resolve().parents[1] / "trajectoire_2.csv")
    track = circuit.loops[0]
    print(
        f"centre ({circuit.center[0]:.0f}, {circuit.center[1]:.0f}) "
        f"L={track.length:.0f} mm "
        f"conflit {circuit.conflict_radius_mm:.0f} mm "
        f"stockage {circuit.storage_radius_mm:.0f} mm"
    )
    for index, gate in enumerate(track.gates, start=1):
        print(
            f"passage {index}: arrêt={gate.stop_s:.0f} entrée={gate.entry_s:.0f} "
            f"sortie={gate.exit_s:.0f} fin stockage={gate.storage_exit_s:.0f} "
            f"traversée={(gate.exit_s - gate.stop_s) / CRUISE_MM_S:.1f} s"
        )
