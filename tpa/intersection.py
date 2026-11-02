"""Décision du croisement et du capteur, sans le brick.

Le centre est celui du huit de trajectoire_2.csv, tour 1, dans le repère
qui part de (0, 0) cap 0. Les rayons sont les mêmes que la simulation.
"""

from math import sqrt

CROSSING_MM = (183.0, -898.0)
CONFLICT_RADIUS_MM = 220.0
STORAGE_RADIUS_MM = 480.0
FOLLOW_GAP_MM = 280.0
SENSOR_RANGE_MM = 800.0
SENSOR_FAULT_MM = 2500


def distance_to_crossing(x_mm, y_mm):
    dx = x_mm - CROSSING_MM[0]
    dy = y_mm - CROSSING_MM[1]
    return sqrt(dx * dx + dy * dy)


def classify(dist_mm, clearing):
    """Zone et mémorisation de la sortie du disque."""
    if dist_mm <= CONFLICT_RADIUS_MM:
        return "conflit", True
    if clearing and dist_mm <= STORAGE_RADIUS_MM:
        return "sortie", True
    if dist_mm <= STORAGE_RADIUS_MM:
        return "stockage", False
    return "ligne", False


def sensor_scale(sensor_mm):
    """1 loin, 0 à la garde. None ou une mesure absurde : rien devant."""
    if sensor_mm is None or sensor_mm >= SENSOR_FAULT_MM:
        return 1.0
    if sensor_mm <= FOLLOW_GAP_MM:
        return 0.0
    if sensor_mm >= SENSOR_RANGE_MM:
        return 1.0
    return (sensor_mm - FOLLOW_GAP_MM) / (SENSOR_RANGE_MM - FOLLOW_GAP_MM)


def granted(phase, robot_id, inside):
    """Un robot déjà dans le disque finit sa traversée. Sinon il obéit au feu."""
    if inside:
        return True
    if not phase:
        return True
    phase_name = phase.get("phase")
    closed = phase.get("all_red") or phase_name in ("all_red", "occupied")
    if not closed:
        return True
    green = phase.get("green") or []
    return robot_id in green


def speed_command(base_speed, dist_mm, clearing, phase, robot_id, sensor_mm):
    """Vitesse moteur, zone, et le drapeau de sortie."""
    zone, clearing = classify(dist_mm, clearing)
    inside = zone == "conflit"
    scale = sensor_scale(sensor_mm)
    if zone == "stockage" and not granted(phase, robot_id, inside):
        return 0.0, zone, clearing
    return base_speed * scale, zone, clearing


if __name__ == "__main__":
    open_phase = {"phase": "open", "green": ["A", "B"], "all_red": False}
    red = {"phase": "occupied", "green": ["B"], "all_red": False}
    all_red = {"phase": "all_red", "green": [], "all_red": True}

    speed, zone, clearing = speed_command(400, 2000, False, open_phase, "A", None)
    assert speed == 400 and zone == "ligne", (speed, zone)

    speed, zone, _ = speed_command(400, 2000, False, open_phase, "A", 100)
    assert speed == 0 and zone == "ligne"

    speed, zone, _ = speed_command(400, 400, False, red, "A", None)
    assert speed == 0 and zone == "stockage"

    speed, zone, clearing = speed_command(400, 100, False, red, "A", None)
    assert speed == 400 and zone == "conflit" and clearing

    speed, zone, clearing = speed_command(400, 300, True, all_red, "A", None)
    assert speed == 400 and zone == "sortie" and clearing

    speed, zone, _ = speed_command(400, 400, False, all_red, "A", 500)
    assert speed == 0 and zone == "stockage"

    speed, zone, _ = speed_command(400, 2000, False, red, "B", 540)
    assert zone == "ligne" and 0 < speed < 400

    print("intersection ok")
