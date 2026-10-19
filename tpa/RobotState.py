from math import cos, pi, sin

LAP_MIN_MM = 2500
LAP_SWING_DEG = 90
LAP_HEADING_DEG = 30
from pybricks.parameters import Port
from pybricks.tools import StopWatch
from pybricks.hubs import EV3Brick

from RobotLCD import RobotLCD
from RobotLogger import RobotLogger
from RobotDrive import RobotDrive
from RobotSensor import RobotSensor


def integrate_pose(pose, delta_mm, heading_deg):
    """px += cos(theta) * distance, py += sin(theta) * distance."""
    heading_rad = heading_deg * pi / 180.0
    return (
        pose[0] + cos(heading_rad) * delta_mm,
        pose[1] + sin(heading_rad) * delta_mm,
        heading_deg,
    )


class HeadingKalman:
    """Angle: prediction from a turn rate, correction from the gyro."""

    def __init__(self, q_deg2_s=25.0, r_deg2=4.0):
        self.q = q_deg2_s
        self.r = r_deg2
        self.angle = 0.0
        self.variance = 1.0
        self.gain = 0.0
        self.innovation = 0.0

    def reset(self):
        self.angle = 0.0
        self.variance = 1.0
        self.gain = 0.0
        self.innovation = 0.0

    def update(self, turn_rate_deg_s, measurement_deg, dt):
        self.angle += turn_rate_deg_s * dt
        self.variance += self.q * dt
        if measurement_deg is None:
            self.gain = 0.0
            self.innovation = 0.0
            return self.angle
        self.innovation = measurement_deg - self.angle
        weight = self.variance + self.r
        self.gain = self.variance / weight if weight > 0.0 else 0.0
        self.angle += self.gain * self.innovation
        self.variance = (1.0 - self.gain) * self.variance
        return self.angle


class RobotState:
    def __init__(self, sensor_port=Port.S1, gyro_port=Port.S3, sample_period_ms=100,
                 wheel_diameter=56.0, axle_track=114.0, q=25.0, r=4.0,
                 filename="trajectoire.csv"):
        self.ev3 = EV3Brick()
        self.lastColor = None
        self.lastDistance = -1
        self.sample_period_ms = sample_period_ms
        self.wheel_diameter = wheel_diameter
        self.axle_track = axle_track
        self.LCD = RobotLCD(self.ev3)
        self.sensor = RobotSensor(sensor_port, gyro_port=gyro_port)
        self.drive = RobotDrive(wheel_diameter=wheel_diameter, axle_track=axle_track)
        self.watch = StopWatch()
        self.kalman = HeadingKalman(q, r)
        self.logger = RobotLogger(filename, {
            "D_mm": wheel_diameter,
            "V_mm": axle_track,
            "q_deg2_s": q,
            "r_deg2": r,
            "sample_ms": sample_period_ms,
        })
        self.reset_localization()

    def updateLastColor(self, color):
        self.lastColor = color

    def updateLastDistance(self, distance):
        self.lastDistance = distance

    def updateLCD(self, text):
        self.LCD.Text(text)

    def close(self):
        self.logger.close()

    def _note_lap(self, distance):
        """Un tour du huit: le cap commande revient vers 0 apres un virage des deux cotes."""
        heading = self.command_heading
        if heading > self._lap_heading_max:
            self._lap_heading_max = heading
        if heading < self._lap_heading_min:
            self._lap_heading_min = heading
        near_start = abs(heading) <= LAP_HEADING_DEG
        swung = (self._lap_heading_max >= LAP_SWING_DEG and
                 self._lap_heading_min <= -LAP_SWING_DEG)
        if near_start and swung and distance - self._lap_distance >= LAP_MIN_MM:
            self.lap += 1
            self._lap_distance = distance
            self._lap_heading_min = 0.0
            self._lap_heading_max = 0.0
            print("Tour", self.lap)

    def note_command(self):
        now = self.watch.time()
        if self._command_ms is None:
            self._command_ms = now
            return
        dt = (now - self._command_ms) / 1000.0
        self._command_ms = now
        if dt <= 0.0 or dt > 0.2:
            return
        self.command_distance += self.drive.command_speed_mm_s * dt
        self.command_heading += self.drive.command_turn_rate_deg_s * dt

    def reset_localization(self):
        self.drive.reset_distance()
        self.sensor.reset_gyro()
        self.watch.reset()
        self.command_distance = 0.0
        self.command_heading = 0.0
        self._command_ms = None
        self._last_command_distance = 0.0
        self._last_distance = 0.0
        self._last_sample_ms = self.watch.time()
        self._last_gyro_angle = None
        self.lap = 1
        self._lap_distance = 0.0
        self._lap_heading_min = 0.0
        self._lap_heading_max = 0.0
        self._screen_ms = 0
        self.history = []
        self.poses = {
            "command": (0.0, 0.0, 0.0),
            "odometry": (0.0, 0.0, 0.0),
            "gyro": (0.0, 0.0, 0.0),
            "kalman": (0.0, 0.0, 0.0),
        }
        self.pose = self.poses["odometry"]
        self.odometry_heading = 0.0
        self.gyro_heading = None
        self.kalman.reset()

    def update_localization(self, mode="kalman", force=False, reflection=None):
        now = self.watch.time()
        dt = (now - self._last_sample_ms) / 1000.0
        if not force and now - self._last_sample_ms < self.sample_period_ms:
            return self.pose
        if dt <= 0.0 and self.history:
            return self.pose
        self._last_sample_ms = now
        distance, speed, odometry_angle, turn_rate = self.drive.state()
        delta_odometry = distance - self._last_distance
        delta_command = self.command_distance - self._last_command_distance
        self._last_distance = distance
        self._last_command_distance = self.command_distance
        self.odometry_heading = odometry_angle
        gyro_angle = self.sensor.gyro_angle()
        gyro_rate = None
        if gyro_angle is not None and self._last_gyro_angle is not None and dt > 0.0:
            gyro_rate = (gyro_angle - self._last_gyro_angle) / dt
        self._last_gyro_angle = gyro_angle
        self.gyro_heading = gyro_angle
        measured = gyro_angle
        filtered = self.kalman.update(turn_rate, measured, dt if dt > 0.0 else 0.0)
        self.poses["command"] = integrate_pose(
            self.poses["command"], delta_command, self.command_heading)
        self.poses["odometry"] = integrate_pose(
            self.poses["odometry"], delta_odometry, odometry_angle)
        gyro_heading = self.command_heading if gyro_angle is None else gyro_angle
        self.poses["gyro"] = integrate_pose(
            self.poses["gyro"], delta_command, gyro_heading)
        self.poses["kalman"] = integrate_pose(
            self.poses["kalman"], delta_odometry, filtered)
        self._note_lap(distance)
        self.pose = self.poses[mode] if mode in self.poses else self.poses["kalman"]
        left_angle, right_angle = self.drive.wheel_angles()
        row = {
            "time_s": now / 1000.0,
            "dt_s": dt,
            "lap": self.lap,
            "command_speed_mm_s": self.drive.command_speed_mm_s,
            "command_turn_rate_deg_s": self.drive.command_turn_rate_deg_s,
            "command_distance_mm": self.command_distance,
            "command_heading_deg": self.command_heading,
            "x_command_mm": self.poses["command"][0],
            "y_command_mm": self.poses["command"][1],
            "distance_mm": distance,
            "speed_mm_s": speed,
            "odometry_heading_deg": odometry_angle,
            "turn_rate_deg_s": turn_rate,
            "x_odometry_mm": self.poses["odometry"][0],
            "y_odometry_mm": self.poses["odometry"][1],
            "gyro_heading_deg": gyro_angle,
            "gyro_rate_deg_s": gyro_rate,
            "x_gyro_mm": self.poses["gyro"][0],
            "y_gyro_mm": self.poses["gyro"][1],
            "kalman_heading_deg": filtered,
            "kalman_gain": self.kalman.gain,
            "innovation_deg": self.kalman.innovation,
            "x_kalman_mm": self.poses["kalman"][0],
            "y_kalman_mm": self.poses["kalman"][1],
            "left_angle_deg": left_angle,
            "right_angle_deg": right_angle,
            "reflection": reflection,
        }
        self.history.append(row)
        self.logger.log(row)
        if now - self._screen_ms >= 1000:
            self._screen_ms = now
            self.updateLCD("Tour " + str(self.lap))
        return self.pose

    def get_pose(self):
        return self.pose

    def get_history(self):
        return tuple(self.history)
