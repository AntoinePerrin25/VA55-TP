import time

class RobotLogger:
    def __init__(self, filename="robot_log.csv"):
        self.filename = filename
        self.start_time = time.time()

        with open(self.filename, "w") as file:
            file.write("Temps (s);Couleur;Distance (cm)\n")

    def log(self, robot_state):
        elapsed_time = time.time() - self.start_time

        with open(self.filename, "a") as file:
            file.write(
                str(round(elapsed_time, 2)) + ";" +
                str(robot_state.lastColor) + ";" +
                str(robot_state.lastDistance) + "\n"
            )