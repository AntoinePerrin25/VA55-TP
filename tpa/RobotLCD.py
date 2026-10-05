import string

from pybricks.hubs import EV3Brick
from pybricks.parameters import Color
from pybricks.tools import wait

class RobotLCD:
    def __init__(self, ev3):
        self.screen = ev3.screen
        self.text = "Connected"
    def Text(self, text:str):
        self.text = text
        self.screen.clear()
        self.screen.draw_text(0, 0, text, text_color=Color.BLACK, background_color=None)