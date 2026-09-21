#!/usr/bin/env pybricks-micropython

from pybricks.hubs import EV3Brick
from pybricks.parameters import Color
from pybricks.tools import wait


class SonLumiere(object):
    def __init__(self):
        self.ev3 = EV3Brick()

    def beep(self, frequency=500, duration=100):
        self.ev3.speaker.beep(frequency, duration)

    def allumer(self, couleur):
        self.ev3.light.on(couleur)

    def eteindre(self):
        self.ev3.light.off()

    def clignoter(self, couleur, repetitions=3, duree=200):
        for _ in range(repetitions):
            self.allumer(couleur)
            wait(duree)
            self.eteindre()
            wait(duree)


_CLOWN = (
    (262, 80), (330, 80), (392, 80), (523, 80), (659, 80),
    (392, 80), (523, 80), (659, 80),
    (523, 80), (392, 80), (330, 80), (262, 160),
    (208, 80), (262, 80), (311, 80), (415, 80), (523, 80),
    (311, 80), (415, 80), (523, 80),
    (415, 80), (311, 80), (262, 80), (208, 160),
    (220, 80), (262, 80), (330, 80), (440, 80), (523, 80),
    (330, 80), (440, 80), (523, 80),
    (440, 80), (330, 80), (262, 80), (220, 160),
    (233, 80), (294, 80), (349, 80), (466, 80), (587, 80),
    (349, 80), (466, 80), (587, 80), (698, 80), (932, 80),
    (1175, 80), (1397, 240),
    (784, 100), (784, 100), (784, 100), (784, 100),
    (880, 100), (932, 160), (784, 100), (880, 100), (932, 160),
    (1047, 100), (1047, 100), (1047, 100), (1047, 100),
    (1175, 100), (1245, 160), (1047, 100), (1175, 100), (1245, 160),
    (1397, 100), (1397, 100), (1397, 100), (1245, 100),
    (1175, 100), (1047, 100), (932, 100), (880, 100),
    (784, 400),
)


if __name__ == "__main__":
    io = SonLumiere()
    io.allumer(Color.GREEN)
    for f, d in _CLOWN:
        io.beep(f, d)
        wait(15)
    io.clignoter(Color.ORANGE, 2, 150)
    io.eteindre()
