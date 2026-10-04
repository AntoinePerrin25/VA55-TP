from pybricks.parameters import Button
from pybricks.tools import StopWatch, wait


class RobotLineFollower:
    def __init__(
        self,
        robot,
        speed=400,
        setpoint=50,
        period_ms=5,
        kp=1.0,
        ki=0.85,
        kd=0.0175,
        # kp=2.0,
        # ki=1.8,
        # kd=0.35,
        max_steering=300,
        integral_limit=100,
        derivative_filter=0.15,
    ):
        self.robot = robot
        self.speed = speed
        self.setpoint = setpoint
        self.period_ms = period_ms
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_steering = max_steering
        self.integral_limit = integral_limit
        self.derivative_filter = derivative_filter

    def _limit(self, value, minimum, maximum):
        return max(minimum, min(value, maximum))

    def _open_log(self, filename, mode):
        log = open(filename, "w")
        log.write("time_ms,reflection,error,integral,derivative,steering,mode\n")
        return log

    def run_bang_bang(self, filename="bang_bang.csv"):
        log = self._open_log(filename, "bang_bang")
        watch = StopWatch()
        threshold = self.robot.sensor.reflection_threshold

        try:
            while Button.CENTER not in self.robot.ev3.buttons.pressed():
                reflection = self.robot.sensor.getReflection()
                error = reflection - self.setpoint
                steering = -self.max_steering if reflection <= threshold else self.max_steering
                self.robot.drive.drive(self.speed, steering)
                log.write("{0},{1},{2},0,0,{3},bang_bang\n".format(
                    watch.time(), reflection, error, steering
                ))
                wait(self.period_ms)
        finally:
            self.robot.drive.stop()
            self.robot.close()
            log.close()

    def run_pid(
        self,
        filename="suivi_pid.csv",
        target_distance_mm=None,
        localization_mode="kalman",
    ):
        log = self._open_log(filename, "pid")
        watch = StopWatch()
        integral = 0
        previous_error = 0
        previous_time = watch.time()
        filtered_derivative = 0
        if target_distance_mm is not None:
            self.robot.drive.reset_distance()
        self.robot.reset_localization()

        try:
            while Button.CENTER not in self.robot.ev3.buttons.pressed():
                if (
                    target_distance_mm is not None
                    and self.robot.drive.distance_mm() >= target_distance_mm
                ):
                    break
                reflection = self.robot.sensor.getReflection()
                error = reflection - self.setpoint
                current_time = watch.time()
                dt = max(current_time - previous_time, 1) / 1000.0
                raw_derivative = (error - previous_error) / dt
                filtered_derivative = (
                    self.derivative_filter * raw_derivative
                    + (1 - self.derivative_filter) * filtered_derivative
                )
                derivative = filtered_derivative
                previous_error = error
                previous_time = current_time
                integral_candidate = integral + error * dt
                integral_candidate = self._limit(
                    integral_candidate, -self.integral_limit, self.integral_limit
                )
                proportional_derivative = self.kp * error + self.kd * derivative
                candidate_steering = (
                    proportional_derivative + self.ki * integral_candidate
                )
                if not (
                    abs(candidate_steering) > self.max_steering
                    and candidate_steering * error > 0
                ):
                    integral = integral_candidate
                steering = proportional_derivative + self.ki * integral
                steering = self._limit(steering, -self.max_steering, self.max_steering)
                self.robot.drive.drive(self.speed, steering)
                self.robot.update_localization(localization_mode)
                log.write("{0},{1},{2},{3},{4},{5},pid\n".format(
                    watch.time(), reflection, error, integral, derivative, steering
                ))
                wait(self.period_ms)
        finally:
            self.robot.drive.stop()
            self.robot.close()
            log.close()