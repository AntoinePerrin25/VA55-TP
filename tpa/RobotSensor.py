from pybricks.ev3devices import ColorSensor, GyroSensor
from pybricks.parameters import Color, Port


REFLECTION_THRESHOLD = 20

class RobotSensor:
    def __init__(
        self,
        port=Port.S3,
        reflection_threshold=REFLECTION_THRESHOLD,
        gyro_port=Port.S2,
    ):
        self.sensor = ColorSensor(port)
        self.reflection_threshold = reflection_threshold
        self.gyro = None
        if gyro_port is not None:
            try:
                self.gyro = GyroSensor(gyro_port)
            except OSError:
                self.gyro = None

    def getColor(self):
        measured_color = self.sensor.color()
        if measured_color == Color.ORANGE:
            return Color.ORANGE
        if measured_color == Color.BLACK or self.getReflection() <= self.reflection_threshold:
            return Color.BLACK
        return Color.RED

    def raw_color(self):
        return self.sensor.color()

    def is_orange(self):
        return self.raw_color() == Color.ORANGE

    def getReflection(self):
        return self.sensor.reflection()

    def color(self):
        return self.getColor()

    def gyro_angle(self):
        return None if self.gyro is None else self.gyro.angle()

    def gyro_rate(self):
        return None if self.gyro is None else self.gyro.speed()

    def reset_gyro(self):
        if self.gyro is not None:
            self.gyro.reset_angle(0)