#!/usr/bin/env pybricks-micropython

from pybricks.ev3devices import ColorSensor
from pybricks.parameters import Color, Port
from pybricks.tools import wait

# seil reflexion %, < = ligne noire au sol.
LINE_REFLECTION_MAX = 20
REFL_ALPHA = 0.65

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
    def __init__(self, port=Port.S3, zones=None, line_reflection_max=LINE_REFLECTION_MAX):
        self.port = port
        self._sensor = ColorSensor(port)
        self._zones = DEFAULT_ZONES if zones is None else zones
        self.line_reflection_max = line_reflection_max
        self._refl = None

    def color(self):
        return self._sensor.color()

    def color_name(self):
        detected = self.color()
        if detected is None:
            return None
        return _COLOR_NAMES.get(detected)

    def refresh(self):
        val = self._sensor.reflection()
        if val < 0:
            val = 0
        elif val > 100:
            val = 100
        if self._refl is None:
            self._refl = val
        else:
            self._refl = int(round(REFL_ALPHA * val + (1.0 - REFL_ALPHA) * self._refl))
        return self._refl

    def reflection(self):
        if self._refl is None:
            return self.refresh()
        return self._refl

    def zone(self):
        if self.sur_ligne():
            return self._zones.get(Color.BLACK, "ligne")
        return self._zones.get(Color.WHITE, "sol")

    def is_zone(self, name):
        return self.zone() == name

    def sur_ligne(self):
        return self.reflection() <= self.line_reflection_max


if __name__ == "__main__":
    capteur = CapteurCouleur()
    for _ in range(2000):
        capteur.refresh()
        print(
            "zone={0} refl={1} ligne={2}".format(
                capteur.zone(),
                capteur.reflection(),
                capteur.sur_ligne(),
            )
        )
        wait(200)
