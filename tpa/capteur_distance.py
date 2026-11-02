#!/usr/bin/env pybricks-micropython

from pybricks.ev3devices import InfraredSensor, UltrasonicSensor
from pybricks.parameters import Port
from pybricks.tools import wait

# renvoie 0–100 (relatif) 100 ≈ 700 mm.
IR_MM_PER_UNIT = 7

TYPE_US = "us"
TYPE_IR = "ir"


class CapteurDistance(object):
    def __init__(self, port=Port.S2, sensor_type=None):
        self.port = port
        self.kind = None
        self._sensor = None
        self._connect(sensor_type)

    def _connect(self, sensor_type):
        # --------- SENSOR TYPE
        if sensor_type == TYPE_IR:
            self._sensor = InfraredSensor(self.port)
            self.kind = TYPE_IR
            return
        if sensor_type == TYPE_US:
            self._sensor = UltrasonicSensor(self.port)
            self.kind = TYPE_US
            return
        if sensor_type is not None:
            raise ValueError("'us', 'ir' ou None")


        # --------- SENSOR CONFIG

        try:
            self._sensor = UltrasonicSensor(self.port)
            self.kind = TYPE_US
            return
        except Exception:
            pass
        try:
            self._sensor = InfraredSensor(self.port)
            self.kind = TYPE_IR
            return
        except Exception:
            pass
        raise OSError("pas de capteur")

    def distance(self):
        """Millimètres devant le robot. None si rien n'est vu ou si la mesure est absurde."""
        try:
            raw = self._sensor.distance()
        except Exception:
            return None
        if raw is None:
            return None
        if self.kind == TYPE_IR:
            mm = int(raw * IR_MM_PER_UNIT)
        else:
            mm = raw
        # 2550 est la valeur d'erreur de l'ultrason, pas un obstacle.
        if mm <= 0 or mm >= 2500:
            return None
        return int(mm)


if __name__ == "__main__":
    capteur = CapteurDistance()
    print("kind={0}".format(capteur.kind))
    for _ in range(1000):
        print(capteur.distance())
        wait(200)
