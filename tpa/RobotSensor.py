from pybricks.ev3devices import ColorSensor
from pybricks.parameters import Color, Port


REFLECTION_THRESHOLD = 20

class RobotSensor:
    def __init__(self, port=Port.S3, reflection_threshold=REFLECTION_THRESHOLD):
        self.sensor = ColorSensor(port)
        self.reflection_threshold = reflection_threshold

    def getColor(self):
        if self.getReflection() <= self.reflection_threshold:
            return Color.BLACK
        return Color.RED

    def getReflection(self):
        return self.sensor.reflection()

    def color(self):
        return self.getColor()