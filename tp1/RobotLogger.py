#!/usr/bin/env pybricks-micropython

import time


class RobotLogger(object):
    def __init__(self, filename="log_pid.csv"):
        self.filename = filename
        self.start_time = time.time()
        with open(self.filename, "w") as file:
            file.write(
                "Temps (s);Reflection;Erreur;Commande (deg/s);Vitesse (mm/s);Zone;Distance (mm)\n"
            )

    def log(self, robot_state):
        elapsed_time = time.time() - self.start_time
        with open(self.filename, "a") as file:
            file.write(
                "{0};{1};{2};{3};{4};{5};{6}\n".format(
                    round(elapsed_time, 2),
                    robot_state.reflection,
                    round(robot_state.erreur, 1),
                    round(robot_state.commande, 1),
                    round(robot_state.vitesse, 1),
                    robot_state.zone,
                    robot_state.lastDistance,
                )
            )
