#!/usr/bin/env pybricks-micropython

from pybricks.ev3devices import Motor
from pybricks.parameters import Port, Direction, Stop
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
        self.left = Motor(left_port, Direction.COUNTERCLOCKWISE)
        self.right = Motor(right_port, Direction.CLOCKWISE)
        self.wheel_diameter = wheel_diameter
        self.axle_track = axle_track
        self._ratio = float(axle_track) / float(wheel_diameter)

    def forward(self, speed):
        self.left.run(-speed) 
        self.right.run(speed)

    def rotate(self, angle, aSpeed):
        if aSpeed == 0 or angle == 0:
            return
        motor_angle = self._ratio * angle
        motor_speed = abs(self._ratio * aSpeed)
        self.left.run_angle(-motor_speed, -motor_angle, Stop.HOLD, False)
        self.right.run_angle(motor_speed, motor_angle, Stop.HOLD, True)

    def stop(self):
        self.left.hold()
        self.right.hold()


if __name__ == "__main__":
    robot = Pilotage()
    robot.forward(800)
    wait(1000)
    robot.stop()
    wait(500)
    robot.rotate(360, 800)
    wait(1000)
    robot.stop()
