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
        """ 0–100 conversion en 0–700 mm."""
        raw = self._sensor.distance()

        # TODO: SOMETIMES GET 2550 OR TOO BIG VALUE, NEED FIX
        if self.kind == TYPE_IR:
            return int(raw * IR_MM_PER_UNIT)
        return raw


if __name__ == "__main__":
    capteur = CapteurDistance()
    print("kind={0}".format(capteur.kind))
    for _ in range(1000):
        print(capteur.distance())
        wait(200)
