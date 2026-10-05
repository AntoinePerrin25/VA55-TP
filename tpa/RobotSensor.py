from pybricks.ev3devices import ColorSensor, GyroSensor
from pybricks.parameters import Port


REFLECTION_THRESHOLD = 20

class RobotSensor:
    def __init__(
        self,
        port=Port.S1,
        reflection_threshold=REFLECTION_THRESHOLD,
        gyro_port=Port.S3,
    ):
        self.sensor = ColorSensor(port)
        self.reflection_threshold = reflection_threshold
        self.sensor.reflection()
        self.gyro = None
        if gyro_port is not None:
            try:
                self.gyro = GyroSensor(gyro_port)
            except OSError:
                self.gyro = None

    def getReflection(self):
        return self.sensor.reflection()

    def gyro_angle(self):
        return None if self.gyro is None else self.gyro.angle()

    def reset_gyro(self):
        if self.gyro is not None:
            self.gyro.reset_angle(0)