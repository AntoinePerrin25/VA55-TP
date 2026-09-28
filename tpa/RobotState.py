from pybricks.ev3devices import ColorSensor
from pybricks.parameters import Color, Port
from pybricks.hubs import EV3Brick

from RobotLCD import RobotLCD
from RobotLogger import RobotLogger
from RobotDrive import RobotDrive
from RobotSensor import RobotSensor


class RobotState:
    def __init__(self, sensor_port=Port.S3):
        self.ev3 = EV3Brick()
        self.lastColor = None
        self.lastDistance = -1
        self.logger = RobotLogger()
        print("RobotState initialized")
        self.LCD = RobotLCD(self.ev3)
        print("RobotLCD initialized")
        self.sensor = RobotSensor(sensor_port)
        print("RobotSensor initialized")
        self.drive = RobotDrive()
        print("RobotDrive initialized")
    def updateLastColor(self, color):
        self.lastColor = color

    def updateLastDistance(self, distance):
        self.lastDistance = distance

    def updateLCD(self, text):
        self.LCD.Text(text)

    def log(self):
        self.logger.log(self)

