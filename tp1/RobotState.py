#!/usr/bin/env pybricks-micropython

from pybricks.hubs import EV3Brick

from RobotLCD import LCD
from RobotLogger import RobotLogger


class RobotState(object):
    def __init__(self, ev3=None, log_filename="log_bangbang.csv"):
        self.ev3 = ev3 if ev3 is not None else EV3Brick()
        self.lastColor = None
        self.lastDistance = -1
        self.reflection = 0
        self.erreur = 0
        self.commande = 0
        self.zone = None
        self.logger = RobotLogger(log_filename)
        self.LCD = LCD(self.ev3)

    def updateLastColor(self, color):
        self.lastColor = color

    def updateLastDistance(self, distance):
        self.lastDistance = distance

    def update(self, color, distance, reflection=0, erreur=0, zone=None, commande=0):
        self.lastColor = color
        self.lastDistance = distance
        self.reflection = reflection
        self.erreur = erreur
        self.zone = zone
        self.commande = commande

    def updateLCD(self, text):
        self.LCD.Text(text)

    def status(self):
        self.LCD.status(self)

    def log(self):
        self.logger.log(self)
