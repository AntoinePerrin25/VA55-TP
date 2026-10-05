from pybricks.ev3devices import Motor
from pybricks.parameters import Direction, Port, Stop

from math import pi


WHEEL_DIAMETER = 56
AXLE_TRACK = 114


class RobotDrive:
    def __init__(
        self,
        left_port=Port.B,
        right_port=Port.C,
        wheel_diameter=WHEEL_DIAMETER,
        axle_track=AXLE_TRACK,
        steering_gain=2.0,
    ):
        self.left = Motor(left_port, Direction.COUNTERCLOCKWISE)
        self.right = Motor(right_port, Direction.CLOCKWISE)
        self.wheel_diameter = wheel_diameter
        self.axle_track = axle_track
        self.steering_gain = steering_gain
        self._ratio = float(axle_track) / float(wheel_diameter)

    def drive(self, speed, steering=0):
        correction = self.steering_gain * steering
        left_speed = speed + correction
        right_speed = speed - correction

        self.left.run(-left_speed)
        self.right.run(right_speed)

    def forward(self, speed):
        self.drive(speed)

    def turn(self, angle, speed):
        self.rotate(angle, speed)

    def rotate(self, angle, speed):
        if speed == 0 or angle == 0:
            return

        motor_angle = self._ratio * angle
        motor_speed = abs(self._ratio * speed)
        self.left.run_angle(-motor_speed, -motor_angle, Stop.HOLD, False)
        self.right.run_angle(motor_speed, motor_angle, Stop.HOLD, True)

    def stop(self):
        self.left.hold()
        self.right.hold()

    def reset_distance(self):
        self.left.reset_angle(0)
        self.right.reset_angle(0)

    def distance_mm(self):
        left_distance = abs(self.left.angle())
        right_distance = abs(self.right.angle())
        average_angle = (left_distance + right_distance) / 2
        return average_angle * pi * self.wheel_diameter / 360