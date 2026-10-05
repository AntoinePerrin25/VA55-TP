#!/usr/bin/env pybricks-micropython

from RobotState import RobotState
from RobotLineFollower import RobotLineFollower

MODE_BANG_BANG = "bang_bang"
MODE_PID = "pid"
EXPERIENCE_TAPIS = "tapis"
EXPERIENCE_LIGNE_1M = "ligne_1m"


MODE = MODE_PID
EXPERIENCE = EXPERIENCE_TAPIS
PID_LOG = "suivi_pid_{0}.csv".format(EXPERIENCE)
TARGET_DISTANCE_MM = 1000 if EXPERIENCE == EXPERIENCE_LIGNE_1M else None

if __name__ == "__main__":
    robot = RobotState()
    follower = RobotLineFollower(robot)
    robot.updateLCD("Suivi " + MODE + " " + EXPERIENCE)
    if MODE == MODE_BANG_BANG:
        follower.run_bang_bang("bang_bang.csv")
    else:
        follower.run_pid(PID_LOG, TARGET_DISTANCE_MM)