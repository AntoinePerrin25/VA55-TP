from math import cos, pi, sin
from pybricks.parameters import Port
from pybricks.tools import StopWatch
from pybricks.hubs import EV3Brick

from RobotLCD import RobotLCD
from RobotLogger import RobotLogger
from RobotDrive import RobotDrive
from RobotSensor import RobotSensor


ORANGE_CONFIRMATION_SAMPLES = 5
MIN_CIRCUIT_TIME_MS = 10000


class RobotState:
    def __init__(self, sensor_port=Port.S3, gyro_port=Port.S2, sample_period_ms=100):
        self.ev3 = EV3Brick()
        self.lastColor = None
        self.lastDistance = -1
        self.logger = RobotLogger()
        print("RobotState initialized")
        self.LCD = RobotLCD(self.ev3)
        print("RobotLCD initialized")
        self.sensor = RobotSensor(sensor_port, gyro_port=gyro_port)
        print("RobotSensor initialized")
        self.drive = RobotDrive()
        print("RobotDrive initialized")
        self.sample_period_ms = sample_period_ms
        self.watch = StopWatch()
        self.pose = (0.0, 0.0, 0.0)
        self.odometry_heading = 0.0
        self.gyro_heading = None
        self._last_distance = 0.0
        self._last_sample_ms = self.watch.time()
        self.history = []
        self._kalman_angle = 0.0
        self._kalman_bias = 0.0
        self._kalman_covariance = [[1.0, 0.0], [0.0, 1.0]]
        self._process_noise = 0.05
        self._measurement_noise = 2.0
        self.current_color = None
        self._orange_active = False
        self._orange_samples = 0
        self._circuit_start_ms = self._last_sample_ms
        self._has_logged_sample = False
    def updateLastColor(self, color):
        self.lastColor = color

    def updateLastDistance(self, distance):
        self.lastDistance = distance

    def updateLCD(self, text):
        self.LCD.Text(text)

    def log(self):
        self.logger.log(self)

    def close(self):
        self.logger.close()

    def reset_localization(self):
        self.drive.reset_distance()
        self.sensor.reset_gyro()
        self.pose = (0.0, 0.0, 0.0)
        self.odometry_heading = 0.0
        self.gyro_heading = 0.0 if self.sensor.gyro is not None else None
        self._last_distance = 0.0
        self._last_sample_ms = self.watch.time()
        self.history = []
        self._kalman_angle = 0.0
        self._kalman_bias = 0.0
        self._kalman_covariance = [[1.0, 0.0], [0.0, 1.0]]
        self.current_color = None
        self._orange_active = False
        self._orange_samples = 0
        self._circuit_start_ms = self._last_sample_ms
        self._has_logged_sample = False

    def _kalman_update(self, rate, measurement, dt):
        angle = self._kalman_angle
        bias = self._kalman_bias
        covariance = self._kalman_covariance
        rate_without_bias = rate - bias
        self._kalman_angle = angle + dt * rate_without_bias
        self._kalman_covariance = [
            [covariance[0][0] + dt * (dt * covariance[1][1] - covariance[0][1] - covariance[1][0]) + self._process_noise,
             covariance[0][1] - dt * covariance[1][1]],
            [covariance[1][0] - dt * covariance[1][1], covariance[1][1] + self._process_noise],
        ]
        if measurement is None:
            return self._kalman_angle
        innovation = measurement - self._kalman_angle
        innovation_covariance = self._kalman_covariance[0][0] + self._measurement_noise
        gain_angle = self._kalman_covariance[0][0] / innovation_covariance
        gain_bias = self._kalman_covariance[1][0] / innovation_covariance
        self._kalman_angle += gain_angle * innovation
        self._kalman_bias += gain_bias * innovation
        self._kalman_covariance = [
            [(1 - gain_angle) * self._kalman_covariance[0][0],
             (1 - gain_angle) * self._kalman_covariance[0][1]],
            [self._kalman_covariance[1][0] - gain_bias * self._kalman_covariance[0][0],
             self._kalman_covariance[1][1] - gain_bias * self._kalman_covariance[0][1]],
        ]
        return self._kalman_angle

    def update_localization(self, mode="kalman", force=False):
        now = self.watch.time()
        dt = max(now - self._last_sample_ms, 1) / 1000.0
        if not force and now - self._last_sample_ms < self.sample_period_ms:
            return self.pose
        self._last_sample_ms = now
        distance, speed, odometry_angle, turn_rate = self.drive.state()
        delta_distance = distance - self._last_distance
        self._last_distance = distance
        self.odometry_heading = odometry_angle
        gyro_angle = self.sensor.gyro_angle()
        gyro_rate = self.sensor.gyro_rate()
        self.gyro_heading = gyro_angle
        self.current_color = str(self.sensor.raw_color())
        if self.sensor.is_orange():
            self._orange_samples += 1
        else:
            self._orange_samples = 0
        orange = self._orange_samples >= ORANGE_CONFIRMATION_SAMPLES
        if orange and not self._orange_active:
            circuit_is_long_enough = now - self._circuit_start_ms >= MIN_CIRCUIT_TIME_MS
            if self._has_logged_sample and circuit_is_long_enough:
                self.logger.start_new_circuit()
                self._circuit_start_ms = now
            else:
                self.logger.reset_circuit_timer()
        self._orange_active = orange
        if mode == "gyro" and gyro_angle is not None:
            heading = gyro_angle
        elif mode == "kalman":
            heading = self._kalman_update(
                turn_rate if gyro_rate is None else gyro_rate,
                gyro_angle,
                dt,
            )
        else:
            heading = odometry_angle
        x, y, _ = self.pose
        heading_radians = heading * pi / 180.0
        self.pose = (
            x + cos(heading_radians) * delta_distance,
            y + sin(heading_radians) * delta_distance,
            heading,
        )
        self.history.append({
            "time_s": now / 1000.0,
            "x_mm": self.pose[0],
            "y_mm": self.pose[1],
            "heading_deg": heading,
            "distance_mm": distance,
            "speed_mm_s": speed,
            "turn_rate_deg_s": turn_rate,
        })
        self.logger.log(self, mode)
        self.updateLCD("Circuit " + str(self.logger.circuit))
        self._has_logged_sample = True
        return self.pose

    def get_pose(self):
        return self.pose

    def get_history(self):
        return tuple(self.history)

