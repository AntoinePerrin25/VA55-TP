"""Règles d'approche du croisement, indépendantes du matériel EV3."""

from math import sqrt

CROSSING_MM = (183.0, -898.0)
CONFLICT_RADIUS_MM = 220.0
STORAGE_RADIUS_MM = 480.0
STOP_RADIUS_MM = 560.0
REQUEST_RADIUS_MM = 720.0
CLEAR_RADIUS_MM = 320.0
FOLLOW_GAP_MM = 280.0
SENSOR_RANGE_MM = 800.0
PHASE_TIMEOUT_MS = 750


def distance_to_crossing(x_mm, y_mm):
    dx = x_mm - CROSSING_MM[0]
    dy = y_mm - CROSSING_MM[1]
    return sqrt(dx * dx + dy * dy)


def sensor_scale(sensor_mm):
    if sensor_mm is None:
        return 1.0
    scale = (sensor_mm - FOLLOW_GAP_MM) / (SENSOR_RANGE_MM - FOLLOW_GAP_MM)
    return max(0.0, min(1.0, scale))


def crossing_state(distance, passage, crossed, permitted):
    """Donne la zone physique et mémorise l'entrée puis la libération."""
    if distance <= CONFLICT_RADIUS_MM:
        return "conflit", "engage", True

    if crossed:
        if passage != "libere" and distance < CLEAR_RADIUS_MM:
            return "sortie", "engage", True
        zone = "sortie" if distance <= STORAGE_RADIUS_MM else "ligne"
        return zone, "libere", distance <= REQUEST_RADIUS_MM

    if passage == "engage" or (distance <= STOP_RADIUS_MM and permitted):
        passage = "engage"
    elif distance <= REQUEST_RADIUS_MM:
        passage = "approche"
    elif passage != "libere":
        passage = "ligne"

    zone = "stockage" if distance <= STORAGE_RADIUS_MM else "ligne"
    return zone, passage, False


def speed_command(base_speed, distance, passage, sensor_mm):
    if distance <= STOP_RADIUS_MM and passage == "approche":
        return 0.0
    return base_speed * sensor_scale(sensor_mm)


if __name__ == "__main__":
    assert crossing_state(650, "ligne", False, False) == ("ligne", "approche", False)
    assert speed_command(400, 550, "approche", None) == 0
    assert crossing_state(550, "approche", False, True) == ("ligne", "engage", False)
    assert crossing_state(450, "engage", False, False) == ("stockage", "engage", False)
    assert crossing_state(210, "engage", False, False) == ("conflit", "engage", True)
    assert crossing_state(300, "engage", True, False) == ("sortie", "engage", True)
    assert crossing_state(330, "engage", True, False) == ("sortie", "libere", True)
    assert crossing_state(730, "libere", True, False) == ("ligne", "libere", False)
    assert speed_command(400, 650, "approche", 280) == 0
    assert speed_command(400, 450, "engage", 540) == 200
    print("intersection EV3 : OK")
