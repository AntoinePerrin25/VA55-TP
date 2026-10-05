#!/usr/bin/env pybricks-micropython

import sys

from pybricks.tools import wait

from RobotDrive import RobotDrive


SPEED = 250
TURN_STEERING = 100


def read_command():
    command = sys.stdin.read(1)
    if command == "\x1b":
        sequence = command + sys.stdin.read(2)
        return {
            "\x1b[A": "F",
            "\x1b[B": "B",
            "\x1b[D": "L",
            "\x1b[C": "R",
        }.get(sequence, "")
    return command


def main():
    drive = RobotDrive()
    drive.stop()
    try:
        while True:
            command = read_command()
            if command == "q":
                break
            if command == "F":
                drive.drive(SPEED, 0)
            elif command == "B":
                drive.drive(-SPEED, 0)
            elif command == "L":
                drive.drive(0, -TURN_STEERING)
            elif command == "R":
                drive.drive(0, TURN_STEERING)
            elif command == "S":
                drive.stop()
            wait(5)
    finally:
        drive.stop()


if __name__ == "__main__":
    main()