from pybricks.ev3devices import ColorSensor, GyroSensor
from pybricks.parameters import Color, Port


REFLECTION_THRESHOLD = 20
ORANGE_RED_MIN = 40
ORANGE_RED_MAX = 50
ORANGE_GREEN_MAX = 20
ORANGE_BLUE_MAX = 15
ORANGE_RED_GREEN_RATIO = 2.5
ORANGE_RED_BLUE_RATIO = 3.0

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
        reflection = self.getReflection()
        if self.is_orange():
            return Color.ORANGE
        if reflection <= self.reflection_threshold:
            return Color.BLACK
        return Color.RED

    def raw_color(self):
        return self.getColor()

    def is_orange(self):
        red, green, blue = self.sensor.rgb()
        if green == 0 or blue == 0:
            return False
        return (
            ORANGE_RED_MIN <= red <= ORANGE_RED_MAX
            and green <= ORANGE_GREEN_MAX
            and blue <= ORANGE_BLUE_MAX
            and red / green >= ORANGE_RED_GREEN_RATIO
            and red / blue >= ORANGE_RED_BLUE_RATIO
        )

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