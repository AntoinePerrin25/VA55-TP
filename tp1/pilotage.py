#!/usr/bin/env pybricks-micropython

from pybricks.ev3devices import Motor
from pybricks.parameters import Port, Direction
from pybricks.robotics import DriveBase
from pybricks.tools import wait

WHEEL_DIAMETER = 56
AXLE_TRACK = 114


class Pilotage(object):
    def __init__(
        self,
        left_port=Port.B,
        right_port=Port.C,
        wheel_diameter=WHEEL_DIAMETER,
        axle_track=AXLE_TRACK,
    ):
        left = Motor(left_port)
        right = Motor(right_port)
        self.base = DriveBase(left, right, wheel_diameter, axle_track)

    def drive(self, speed, turn_rate):
        self.base.drive(speed, turn_rate)

    def forward(self, speed):
        self.base.drive(speed, 0)

    def rotate(self, angle, aSpeed):
        self.base.settings(200, 400, abs(aSpeed), 200)
        self.base.turn(angle)

    def stop(self):
        self.base.stop()


if __name__ == "__main__":
    robot = Pilotage()
    robot.forward(150)
    wait(1000)
    robot.stop()
    wait(500)
    robot.rotate(90, 90)
    robot.stop()
