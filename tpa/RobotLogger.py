import os
import time


FIELDS = (
    "time_s", "dt_s", "lap",
    "command_speed_mm_s", "command_turn_rate_deg_s",
    "command_distance_mm", "command_heading_deg",
    "x_command_mm", "y_command_mm",
    "distance_mm", "speed_mm_s", "odometry_heading_deg", "turn_rate_deg_s",
    "x_odometry_mm", "y_odometry_mm",
    "gyro_heading_deg", "gyro_rate_deg_s",
    "x_gyro_mm", "y_gyro_mm",
    "kalman_heading_deg", "kalman_gain", "innovation_deg",
    "x_kalman_mm", "y_kalman_mm",
    "left_angle_deg", "right_angle_deg",
    "reflection",
)


class RobotLogger:
    def __init__(self, filename="trajectoire.csv", metadata=None):
        self.filename = _unique_filename(filename)
        self.file = open(self.filename, "w")
        self._file_open = True
        self.start_time = time.time()
        meta = metadata or {}
        self.file.write("# " + _meta_line(meta) + "\n")
        self.file.write(";".join(FIELDS) + "\n")
        self.file.flush()

    def close(self):
        if self._file_open:
            self.file.flush()
            self.file.close()
            self._file_open = False

    def log(self, row):
        values = []
        for field in FIELDS:
            value = row.get(field, "")
            if value is None:
                value = ""
            values.append(str(value))
        self.file.write(";".join(values) + "\n")


def _meta_line(metadata):
    parts = []
    for key in sorted(metadata):
        parts.append("{0}={1}".format(key, metadata[key]))
    return " ".join(parts)


def _unique_filename(filename):
    separator = filename.rfind("/")
    directory = filename[:separator] if separator >= 0 else ""
    basename = filename[separator + 1:]
    dot = basename.rfind(".")
    stem = basename[:dot] if dot >= 0 else basename
    extension = basename[dot:] if dot >= 0 else ".csv"
    candidate = filename
    index = 2
    while _exists(candidate):
        name = "{0}_{1}{2}".format(stem, index, extension)
        candidate = directory + "/" + name if directory else name
        index += 1
    return candidate


def _exists(filename):
    try:
        handle = open(filename, "r")
        handle.close()
        return True
    except OSError:
        return False
