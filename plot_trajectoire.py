#!/usr/bin/env python3
"""Trajectoires commande, odometrie, gyro et Kalman.

  python3 plot_trajectoire.py trajectoire.csv
  python3 plot_trajectoire.py --demo

Le CSV vient du robot (tpa/RobotMain.py), separateur ';', premiere ligne '# cle=valeur'.
Les tours sont marques tout seuls. Centre arrete. Les figures separent les estimateurs.
"""

from __future__ import print_function

import argparse
import csv
import math
import os
import random


METHODS = (
    ("command", "Commande PID", "#1f4e79"),
    ("odometry", "Odometrie moteurs", "#c45911"),
    ("gyro", "Gyro + vitesse commande", "#2e7d32"),
    ("kalman", "Kalman", "#6a1b9a"),
)


def read_log(filename):
    meta = {}
    rows = []
    with open(filename, "r") as handle:
        header = None
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                meta.update(_parse_meta(line[1:].strip()))
                continue
            if header is None:
                header = line.split(";")
                continue
            values = line.split(";")
            row = {}
            for index, name in enumerate(header):
                row[name] = values[index] if index < len(values) else ""
            rows.append(row)
    if not rows:
        raise ValueError("aucune mesure dans " + filename)
    return meta, rows


def _parse_meta(text):
    meta = {}
    for part in text.split():
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        try:
            meta[key] = float(value)
        except ValueError:
            meta[key] = value
    return meta


def column(rows, name):
    values = []
    for row in rows:
        text = row.get(name, "")
        if text == "":
            values.append(float("nan"))
        else:
            values.append(float(text))
    return values


def closure(x, y):
    if not x:
        return float("nan")
    return math.hypot(x[-1] - x[0], y[-1] - y[0])


def analyse(rows):
    laps = []
    seen = []
    for row in rows:
        lap = int(float(row.get("lap") or 1))
        if lap not in seen:
            seen.append(lap)
    summary = []
    for name, label, _color in METHODS:
        x = column(rows, "x_{0}_mm".format(name))
        y = column(rows, "y_{0}_mm".format(name))
        summary.append({
            "name": name,
            "label": label,
            "closure_mm": closure(x, y),
            "laps": _lap_closures(rows, name, seen),
        })
    duration = float(rows[-1].get("time_s") or 0) - float(rows[0].get("time_s") or 0)
    return {"duration_s": duration, "samples": len(rows), "laps": seen, "methods": summary}


def _lap_closures(rows, name, laps):
    result = []
    for lap in laps:
        segment = [row for row in rows if int(float(row.get("lap") or 1)) == lap]
        if len(segment) < 2:
            continue
        x = column(segment, "x_{0}_mm".format(name))
        y = column(segment, "y_{0}_mm".format(name))
        result.append({"lap": lap, "closure_mm": closure(x, y)})
    return result


def correct_odometry(rows, distance_scale, heading_scale):
    """Rejoue l'odometrie en corrigeant distance et cap. Strategie offline du sujet."""
    pose = (0.0, 0.0, 0.0)
    previous_distance = float(rows[0].get("distance_mm") or 0)
    previous_heading = float(rows[0].get("odometry_heading_deg") or 0)
    xs = [0.0]
    ys = [0.0]
    for row in rows[1:]:
        distance = float(row.get("distance_mm") or previous_distance)
        heading = float(row.get("odometry_heading_deg") or previous_heading)
        delta = (distance - previous_distance) * distance_scale
        pose = (
            pose[0] + math.cos(heading * heading_scale * math.pi / 180.0) * delta,
            pose[1] + math.sin(heading * heading_scale * math.pi / 180.0) * delta,
            heading * heading_scale,
        )
        xs.append(pose[0])
        ys.append(pose[1])
        previous_distance = distance
        previous_heading = heading
    return xs, ys


def write_html(path, title, paragraphs, images):
    parts = [
        "<!DOCTYPE html><meta charset='utf-8'><title>", title, "</title>",
        "<style>body{font:18px/1.5 Georgia,serif;max-width:920px;margin:2rem auto;color:#1a1a1a}",
        "img{max-width:100%;height:auto} figure{margin:2rem 0}</style>",
        "<h1>", title, "</h1>",
    ]
    for paragraph in paragraphs:
        parts.append("<p>" + paragraph + "</p>")
    for image, caption in images:
        parts.append("<figure><img src='{0}'><figcaption>{1}</figcaption></figure>".format(
            image, caption))
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w") as handle:
        handle.write("".join(parts))


LAP_ALPHA = (0.28, 0.48, 0.72, 1.0)
CLEAN_LAPS = (1, 2, 3)
# Trois essais puis le couple qui rapproche le mieux les fins de tours 1 a 3 de l'origine.
CALIBRATION_TRIALS = (
    (1.00, 1.00, "Initial\nD = 56 mm, V = 114 mm"),
    (0.95, 1.00, "Essai 2\ndistance x 0,95"),
    (1.00, 1.05, "Essai 3\ncap x 1,05"),
    (0.90, 1.03, "Retenu\ndistance x 0,90, cap x 1,03"),
)


def _heading_column(name):
    if name == "command":
        return "command_heading_deg"
    if name == "odometry":
        return "odometry_heading_deg"
    if name == "gyro":
        return "gyro_heading_deg"
    return "kalman_heading_deg"


def _segments(rows, laps):
    allowed = set(laps)
    segments = []
    current = []
    current_lap = None
    for row in rows:
        lap = int(float(row.get("lap") or 1))
        if lap not in allowed:
            if current:
                segments.append((current_lap, current))
                current = []
                current_lap = None
            continue
        if current_lap != lap:
            if current:
                segments.append((current_lap, current))
            current = [row]
            current_lap = lap
        else:
            current.append(row)
    if current:
        segments.append((current_lap, current))
    return segments


def _limits(rows, names, laps, pad=60):
    xs = []
    ys = []
    allowed = set(laps)
    for row in rows:
        if int(float(row.get("lap") or 1)) not in allowed:
            continue
        for name in names:
            xs.append(float(row.get("x_{0}_mm".format(name)) or 0))
            ys.append(float(row.get("y_{0}_mm".format(name)) or 0))
    return (min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad)


def _style_map(axis, limits):
    axis.set_xlim(limits[0], limits[1])
    axis.set_ylim(limits[2], limits[3])
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("x (mm)")
    axis.set_ylabel("y (mm)")
    axis.grid(True, alpha=0.3)
    axis.scatter([0], [0], color="black", s=18, zorder=3)


def plot(filename, out_dir, distance_scale=1.0, heading_scale=1.0):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    meta, rows = read_log(filename)
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    stats = analyse(rows)
    time = column(rows, "time_s")
    laps = stats["laps"]
    clean = [lap for lap in CLEAN_LAPS if lap in laps]
    names = [name for name, _label, _color in METHODS]
    limits = _limits(rows, names, laps)
    lap_colors = ("#6a1b9a", "#00838f", "#ef6c00", "#c62828")

    figure, axes = plt.subplots(2, 2, figsize=(10, 10))
    for axis, (name, label, color) in zip(axes.flat, METHODS):
        for index, (lap, segment) in enumerate(_segments(rows, laps)):
            axis.plot(column(segment, "x_{0}_mm".format(name)),
                      column(segment, "y_{0}_mm".format(name)),
                      color=color, alpha=LAP_ALPHA[index % len(LAP_ALPHA)], linewidth=1.3)
        _style_map(axis, limits)
        axis.set_title(label)
    figure.legend(handles=[
        Line2D([0], [0], color="black", alpha=LAP_ALPHA[index % len(LAP_ALPHA)],
               linewidth=1.6, label="Tour {0}".format(lap))
        for index, lap in enumerate(laps)
    ], loc="lower center", ncol=4, frameon=False)
    figure.suptitle("Les quatre tours, un estimateur par cadre", y=0.98)
    figure.tight_layout(rect=(0, 0.04, 1, 0.96))
    overlay = os.path.join(out_dir, "trajectoires.png")
    figure.savefig(overlay, dpi=140)
    plt.close(figure)

    figure, axes = plt.subplots(1, 2, figsize=(10, 5.2))
    for axis, name, label in (
            (axes[0], "odometry", "Odometrie moteurs"),
            (axes[1], "kalman", "Kalman")):
        for index, (lap, segment) in enumerate(_segments(rows, laps)):
            axis.plot(column(segment, "x_{0}_mm".format(name)),
                      column(segment, "y_{0}_mm".format(name)),
                      color=lap_colors[index % len(lap_colors)],
                      label="Tour {0}".format(lap), linewidth=1.3)
        _style_map(axis, limits)
        axis.set_title(label)
        axis.legend(loc="best", fontsize=8)
    figure.suptitle("Quatre tours. Les moteurs derivent, Kalman tient jusqu'a la sortie")
    figure.tight_layout()
    laps_path = os.path.join(out_dir, "tours_kalman.png")
    figure.savefig(laps_path, dpi=140)
    plt.close(figure)

    figure, axes = plt.subplots(1, 2, figsize=(10, 5.2))
    exit_limits = _limits(rows, ("odometry", "kalman"), laps)
    for axis, name, label, color in (
            (axes[0], "odometry", "Odometrie", "#c45911"),
            (axes[1], "kalman", "Kalman", "#6a1b9a")):
        for _lap, segment in _segments(rows, clean):
            axis.plot(column(segment, "x_{0}_mm".format(name)),
                      column(segment, "y_{0}_mm".format(name)),
                      color="#bdbdbd", linewidth=1.0)
        for _lap, segment in _segments(rows, [lap for lap in laps if lap not in clean]):
            axis.plot(column(segment, "x_{0}_mm".format(name)),
                      column(segment, "y_{0}_mm".format(name)),
                      color=color, linewidth=1.6, label="Tour 4")
        _style_map(axis, exit_limits)
        axis.set_title(label)
        axis.legend(loc="best", fontsize=8)
    figure.suptitle("Tour 4 : sortie de ligne, sur le trace des trois premiers tours")
    figure.tight_layout()
    exit_path = os.path.join(out_dir, "sortie.png")
    figure.savefig(exit_path, dpi=140)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(9, 4.5))
    for name, label, color in METHODS:
        axis.plot(time, column(rows, _heading_column(name)),
                  color=color, label=label, linewidth=1.0)
    seen = set()
    for row in rows:
        lap = int(float(row.get("lap") or 1))
        if lap in seen or lap == 1:
            seen.add(lap)
            continue
        seen.add(lap)
        axis.axvline(float(row["time_s"]), color="#9e9e9e", linewidth=0.8, linestyle="--")
    axis.set_xlabel("temps (s)")
    axis.set_ylabel("cap (deg)")
    axis.set_title("Cap. Les pointilles marquent le debut des tours 2, 3 et 4")
    axis.grid(True, alpha=0.3)
    axis.legend(loc="best", fontsize=9)
    figure.tight_layout()
    headings = os.path.join(out_dir, "caps.png")
    figure.savefig(headings, dpi=140)
    plt.close(figure)

    trials = list(CALIBRATION_TRIALS)
    if (distance_scale, heading_scale) != (1.0, 1.0):
        trials[-1] = (distance_scale, heading_scale, "Retenu\ndistance x {0}, cap x {1}".format(
            distance_scale, heading_scale))
    replayed = []
    for scale_d, scale_h, label in trials:
        xs, ys = correct_odometry(rows, scale_d, scale_h)
        kept_x = []
        kept_y = []
        end_tour3 = float("nan")
        for row, x, y in zip(rows, xs, ys):
            kept_x.append(x)
            kept_y.append(y)
            if int(float(row.get("lap") or 1)) == 3:
                end_tour3 = math.hypot(x, y)
        replayed.append((kept_x, kept_y, label, end_tour3))
    cal_limits = (
        min(min(item[0]) for item in replayed) - 60,
        max(max(item[0]) for item in replayed) + 60,
        min(min(item[1]) for item in replayed) - 60,
        max(max(item[1]) for item in replayed) + 60,
    )
    figure, axes = plt.subplots(2, 2, figsize=(10, 10))
    for axis, (xs, ys, label, end_mm) in zip(axes.flat, replayed):
        axis.plot(xs, ys, color="#c45911", linewidth=1.1)
        _style_map(axis, cal_limits)
        axis.set_title("{0}\nfin du tour 3 : {1:.0f} mm".format(label, end_mm))
    figure.suptitle("Calibration hors ligne de l'odometrie, tour 4 compris", y=0.98)
    figure.tight_layout(rect=(0, 0, 1, 0.96))
    calibration = os.path.join(out_dir, "calibration.png")
    figure.savefig(calibration, dpi=140)
    plt.close(figure)

    lap3 = {}
    for name, label, _color in METHODS:
        segment = [row for row in rows if int(float(row.get("lap") or 1)) == 3]
        if not segment:
            continue
        lap3[label] = math.hypot(
            float(segment[-1].get("x_{0}_mm".format(name)) or 0),
            float(segment[-1].get("y_{0}_mm".format(name)) or 0))
    lines = [
        "{0} echantillons sur {1:.1f} s, tours {2}.".format(
            stats["samples"], stats["duration_s"], ", ".join(str(lap) for lap in laps)),
        "Ecart a l'origine a la fin du tour 3 :",
    ]
    for label, error in lap3.items():
        lines.append("{0} : {1:.0f} mm.".format(label, error))
    lines.append(
        "Le tour 4 quitte la ligne : son ecart final n'est pas une fermeture de boucle.")
    lines.append(
        "Calibration retenue sur les tours 1 a 3 : distance x {0}, cap x {1}, ecart fin de tour 3 {2:.0f} mm.".format(
            trials[-1][0], trials[-1][1], replayed[-1][3]))
    if distance_scale != 1.0 or heading_scale != 1.0:
        lines.append(
            "Echelles passees en argument : distance x {0}, cap x {1}.".format(
                distance_scale, heading_scale))
    text = " ".join(lines)
    html_images = [
        (os.path.basename(overlay),
         "Les quatre tours. Chaque cadre est un estimateur, le trait clair est le tour 1 et le trait fonce le tour 4."),
        (os.path.basename(laps_path),
         "Memes axes. Le tour 4 montre la derive des moteurs et la sortie, Kalman reste groupe avant."),
        (os.path.basename(exit_path),
         "Tour 4 en couleur sur les tours 1 a 3 en gris. L'odometrie suit la sortie, Kalman aussi, avec un autre cap."),
        (os.path.basename(headings),
         "Le filtre suit le gyro. L'ecart avec les moteurs grandit, puis le tour 4 l'ouvre franchement."),
        (os.path.basename(calibration),
         "Trois essais de D et V rejoues sur le meme CSV, puis le couple qui rapproche le plus la fin du tour 3."),
    ]
    # Images are written next to the html when out_dir is the html directory.
    html_path = os.path.join(out_dir, "trajectoire.html")
    write_html(html_path, "Trajectoire du circuit en huit", [text], html_images)
    print(text)
    print(html_path)
    return stats


def _row(**values):
    row = {}
    for key in (
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
        "left_angle_deg", "right_angle_deg", "reflection",
    ):
        row[key] = values.get(key, "")
    return row


class _DemoKalman(object):
    def __init__(self):
        self.angle = 0.0
        self.variance = 1.0
        self.gain = 0.0
        self.innovation = 0.0
        self.q = 25.0
        self.r = 4.0

    def update(self, rate, measurement, dt):
        self.angle += rate * dt
        self.variance += self.q * dt
        self.innovation = measurement - self.angle
        weight = self.variance + self.r
        self.gain = self.variance / weight
        self.angle += self.gain * self.innovation
        self.variance *= (1.0 - self.gain)
        return self.angle


def write_demo(path):
    """Circuit en huit genere avec les equations du robot, D et V volontairement faux."""
    random.seed(1)
    radius = 400.0
    speed = 180.0
    dt = 0.1
    distance_scale = 56.0 / 58.0
    heading_scale = 120.0 / 114.0
    omega = speed / radius * 180.0 / math.pi
    command = (0.0, 0.0, 0.0)
    odometry = (0.0, 0.0, 0.0)
    gyro_pose = (0.0, 0.0, 0.0)
    kalman_pose = (0.0, 0.0, 0.0)
    kalman = _DemoKalman()
    heading = 0.0
    distance_true = 0.0
    distance_measured = 0.0
    bias = 0.15
    rows = []
    time = 0.0
    lap = 1
    # Trois tours : chaque tour est une boucle a gauche puis une boucle a droite.
    for tour in range(3):
        for sign in (1.0, -1.0):
            steps = int((360.0 / omega) / dt)
            for _step in range(steps):
                delta_true = speed * dt
                heading += sign * omega * dt
                distance_true += delta_true
                distance_measured += delta_true * distance_scale
                measured_heading = heading * heading_scale
                gyro = heading + bias * time + random.gauss(0.0, 1.2)
                command = _step_pose(command, delta_true, heading)
                odometry = _step_pose(odometry, delta_true * distance_scale, measured_heading)
                gyro_pose = _step_pose(gyro_pose, delta_true, gyro)
                odom_rate = sign * omega * heading_scale
                filtered = kalman.update(odom_rate, gyro, dt)
                kalman_pose = _step_pose(kalman_pose, delta_true * distance_scale, filtered)
                rows.append(_row(
                    time_s=round(time, 3), dt_s=dt, lap=lap,
                    command_speed_mm_s=speed, command_turn_rate_deg_s=sign * omega,
                    command_distance_mm=distance_true, command_heading_deg=heading,
                    x_command_mm=command[0], y_command_mm=command[1],
                    distance_mm=distance_measured, speed_mm_s=speed * distance_scale,
                    odometry_heading_deg=measured_heading, turn_rate_deg_s=odom_rate,
                    x_odometry_mm=odometry[0], y_odometry_mm=odometry[1],
                    gyro_heading_deg=gyro, gyro_rate_deg_s=sign * omega + bias,
                    x_gyro_mm=gyro_pose[0], y_gyro_mm=gyro_pose[1],
                    kalman_heading_deg=filtered, kalman_gain=kalman.gain,
                    innovation_deg=kalman.innovation,
                    x_kalman_mm=kalman_pose[0], y_kalman_mm=kalman_pose[1],
                    left_angle_deg=0, right_angle_deg=0, reflection=50,
                ))
                time += dt
        lap += 1
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    fields = list(rows[0].keys())
    with open(path, "w") as handle:
        handle.write("# D_mm=56 V_mm=114 q_deg2_s=25 r_deg2=4 sample_ms=100\n")
        handle.write(";".join(fields) + "\n")
        for row in rows:
            handle.write(";".join(str(row[field]) for field in fields) + "\n")
    return distance_scale, heading_scale


def _step_pose(pose, delta_mm, heading_deg):
    rad = heading_deg * math.pi / 180.0
    return (
        pose[0] + math.cos(rad) * delta_mm,
        pose[1] + math.sin(rad) * delta_mm,
        heading_deg,
    )


def main():
    parser = argparse.ArgumentParser(description="Figures du circuit en huit")
    parser.add_argument("csv", nargs="?", help="CSV du robot")
    parser.add_argument("--demo", action="store_true",
                        help="genere un huit avec D et V faux, puis les figures")
    parser.add_argument("--out", default="TP2/figures")
    parser.add_argument("--distance-scale", type=float, default=1.0)
    parser.add_argument("--heading-scale", type=float, default=1.0)
    args = parser.parse_args()
    filename = args.csv
    distance_scale = args.distance_scale
    heading_scale = args.heading_scale
    if args.demo:
        filename = os.path.join("TP2", "trajectoire_demo.csv")
        distance_scale, heading_scale = write_demo(filename)
        # La correction offline annule exactement l'erreur injectee.
        distance_scale = 1.0 / distance_scale
        heading_scale = 1.0 / heading_scale
    if not filename:
        parser.error("donner un CSV ou --demo")
    plot(filename, args.out, distance_scale, heading_scale)


if __name__ == "__main__":
    main()
