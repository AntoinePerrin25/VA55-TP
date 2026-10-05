import time
import os

class RobotLogger:
    def __init__(self, filename="robot_log.csv"):
        separator = filename.rfind("/")
        directory = filename[:separator] if separator >= 0 else ""
        basename = filename[separator + 1:]
        dot = basename.rfind(".")
        stem = basename[:dot] if dot >= 0 else basename
        extension = basename[dot:] if dot >= 0 else ".csv"
        self._directory = directory
        self._stem = stem
        self._extension = extension or ".csv"
        self.circuit = 1
        self.start_time = time.time()
        self.circuit_start_time = time.time()
        self._remove_previous_circuits()
        self.filename = self._circuit_filename()
        self.file = open(self.filename, "w")
        self._file_open = True
        self.file.write(
            "time_s;x_mm;y_mm;odometry_heading_deg;gyro_heading_deg;"
            "filtered_heading_deg;distance_mm;speed_mm_s;turn_rate_deg_s;"
            "reflection;color;circuit;lap_time_s;mode\n"
        )
        self.file.flush()

    def _remove_previous_circuits(self):
        number = 1
        while number <= 200:
            filename = "{0}_circuit_{1}{2}".format(
                self._stem, number, self._extension
            )
            if self._directory:
                filename = self._directory + "/" + filename
            try:
                os.remove(filename)
            except OSError:
                pass
            number += 1

    def _circuit_filename(self):
        filename = "{0}_circuit_{1}{2}".format(
            self._stem, self.circuit, self._extension
        )
        if self._directory:
            return self._directory + "/" + filename
        return filename

    def start_new_circuit(self):
        self.close()
        self.circuit += 1
        self.circuit_start_time = time.time()
        self.filename = self._circuit_filename()
        self.file = open(self.filename, "w")
        self._file_open = True
        self.file.write(
            "time_s;x_mm;y_mm;odometry_heading_deg;gyro_heading_deg;"
            "filtered_heading_deg;distance_mm;speed_mm_s;turn_rate_deg_s;"
            "reflection;color;circuit;lap_time_s;mode\n"
        )
        self.file.flush()

    def reset_circuit_timer(self):
        self.circuit_start_time = time.time()

    def close(self):
        if self._file_open:
            self.file.close()
            self._file_open = False

    def log(self, robot_state, mode="odometry"):
        elapsed_time = time.time() - self.start_time
        lap_time = time.time() - self.circuit_start_time
        pose = robot_state.pose
        drive_state = robot_state.drive.state()
        gyro_heading = robot_state.gyro_heading
        reflection = robot_state.sensor.getReflection()
        color = robot_state.current_color
        values = (
            elapsed_time, pose[0], pose[1], robot_state.odometry_heading,
            "" if gyro_heading is None else gyro_heading,
            pose[2], drive_state[0], drive_state[1], drive_state[3],
            reflection, color, self.circuit, lap_time, mode,
        )
        self.file.write(";".join(str(value) for value in values) + "\n")
        self.file.flush()