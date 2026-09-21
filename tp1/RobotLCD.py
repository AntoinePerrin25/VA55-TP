#!/usr/bin/env pybricks-micropython

from pybricks.parameters import Color


class LCD(object):
    def __init__(self, ev3):
        self.screen = ev3.screen

    def Text(self, text):
        self.screen.clear()
        self.screen.draw_text(0, 0, text, text_color=Color.BLACK)

    def status(self, state):
        self.screen.clear()
        self.screen.print("c={0}".format(state.lastColor))
        self.screen.print("d={0}".format(state.lastDistance))
        self.screen.print("r={0}".format(state.reflection))
        self.screen.print("e={0}".format(state.erreur))
