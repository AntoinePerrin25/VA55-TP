#!/usr/bin/env pybricks-micropython

from pybricks.ev3devices import ColorSensor
from pybricks.parameters import Color, Port
from pybricks.tools import wait

# seil reflexion %, < = ligne noire au sol.
LINE_REFLECTION_MAX = 20

DEFAULT_ZONES = {
    Color.BLACK: "ligne",
    Color.WHITE: "sol",
    Color.RED: "rouge",
    Color.BLUE: "bleu",
    Color.GREEN: "vert",
    Color.YELLOW: "jaune",
    Color.BROWN: "marron",
}

_COLOR_NAMES = {
    Color.BLACK: "black",
    Color.BLUE: "blue",
    Color.GREEN: "green",
    Color.YELLOW: "yellow",
    Color.RED: "red",
    Color.WHITE: "white",
    Color.BROWN: "brown",
}


class CapteurCouleur(object):
    def __init__(self, port=Port.S1, zones=None, line_reflection_max=LINE_REFLECTION_MAX):
        self.port = port
        self._sensor = ColorSensor(port)
        self._zones = DEFAULT_ZONES if zones is None else zones
        self.line_reflection_max = line_reflection_max

    def color(self):
        return self._sensor.color()

    def color_name(self):
        detected = self.color()
        if detected is None:
            return None
        return _COLOR_NAMES.get(detected)

    def reflection(self):
        return self._sensor.reflection() # rouge 0–100

    def zone(self):
        detected = self.color()
        if detected is None:
            return None
        return self._zones.get(detected)

    def is_zone(self, name):
        return self.zone() == name

    def sur_ligne(self):
        return self.reflection() <= self.line_reflection_max


if __name__ == "__main__":
    capteur = CapteurCouleur()
    for _ in range(2000):
        print(
            "color={0} zone={1} refl={2} ligne={3}".format(
                capteur.color_name(),
                capteur.zone(),
                capteur.reflection(),
                capteur.sur_ligne(),
            )
        )
        wait(200)
