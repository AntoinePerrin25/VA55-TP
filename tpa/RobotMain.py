#!/usr/bin/env pybricks-micropython

from RobotState import RobotState
from RobotLineFollower import RobotLineFollower

MODE_BANG_BANG = "bang_bang"
MODE_PID = "pid"
EXPERIENCE_TAPIS = "tapis"
EXPERIENCE_LIGNE_1M = "ligne_1m"
LOCALIZATION_ODOMETRY = "odometry"
LOCALIZATION_GYRO = "gyro"
LOCALIZATION_KALMAN = "kalman"


MODE = MODE_PID # [CB]: MODE_PID|MODE_BANG_BANG
EXPERIENCE = EXPERIENCE_TAPIS # [CB]: EXPERIENCE_TAPIS|EXPERIENCE_LIGNE_1M
PID_LOG = "suivi_pid_{0}.csv".format(EXPERIENCE)
LOCALIZATION_MODE = LOCALIZATION_KALMAN # [CB]: LOCALIZATION_ODOMETRY|LOCALIZATION_GYRO|LOCALIZATION_KALMAN
TARGET_DISTANCE_MM = 1000 if EXPERIENCE == EXPERIENCE_LIGNE_1M else None
WHEEL_DIAMETER_MM = 56.0
AXLE_TRACK_MM = 114.0
KALMAN_Q = 25.0  # incertitude du taux de rotation odometrique, deg^2/s
KALMAN_R = 4.0   # incertitude de l'angle gyro, deg^2

if __name__ == "__main__":
    robot = RobotState(
        wheel_diameter=WHEEL_DIAMETER_MM, axle_track=AXLE_TRACK_MM,
        q=KALMAN_Q, r=KALMAN_R, filename="trajectoire.csv")
    follower = RobotLineFollower(robot)
    robot.updateLCD("3 tours\nCentre: stop")
    if MODE == MODE_BANG_BANG:
        follower.run_bang_bang("bang_bang.csv")
    else:
        follower.run_pid(PID_LOG, TARGET_DISTANCE_MM, LOCALIZATION_MODE)