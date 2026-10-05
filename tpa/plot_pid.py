#!/usr/bin/env python3

import argparse
import csv
import os

import matplotlib.pyplot as plt


def read_log(filename):
    with open(filename, newline="") as log_file:
        rows = list(csv.DictReader(log_file))

    if not rows:
        raise ValueError("le fichier ne contient aucune mesure: " + filename)

    def values(column):
        return [float(row[column]) for row in rows]

    return {
        "time": values("time_ms"),
        "reflection": values("reflection"),
        "error": values("error"),
        "integral": values("integral"),
        "derivative": values("derivative"),
        "steering": values("steering"),
    }


def plot_log(filename, data, setpoint):
    label = os.path.basename(filename)
    figure, axes = plt.subplots(3, 1, sharex=True, figsize=(11, 8))
    figure.suptitle(label)

    axes[0].plot(data["time"], data["reflection"], label="Réflexion")
    axes[0].axhline(setpoint, color="black", linestyle="--", label="Consigne")
    axes[0].set_ylabel("Réflexion (%)")
    axes[0].legend()
    axes[0].grid(True)

    axes[1].plot(data["time"], data["error"], color="tab:red", label="Erreur")
    axes[1].axhline(0, color="black", linestyle="--")
    axes[1].set_ylabel("Erreur")
    axes[1].legend()
    axes[1].grid(True)

    axes[2].plot(data["time"], data["steering"], color="tab:green", label="Correction")
    axes[2].plot(data["time"], data["integral"], label="Intégrale")
    axes[2].plot(data["time"], data["derivative"], label="Dérivée")
    axes[2].set_xlabel("Temps (ms)")
    axes[2].set_ylabel("Commande")
    axes[2].legend()
    axes[2].grid(True)

    figure.tight_layout()
    output = os.path.splitext(filename)[0] + ".png"
    figure.savefig(output, dpi=150)
    print(output)


def main():
    parser = argparse.ArgumentParser(description="Tracer les logs du suivi de ligne PID")
    parser.add_argument("logs", nargs="+", help="un ou plusieurs fichiers CSV")
    parser.add_argument("--setpoint", type=float, default=50, help="consigne de réflexion")
    args = parser.parse_args()

    for filename in args.logs:
        plot_log(filename, read_log(filename), args.setpoint)
    plt.show()


if __name__ == "__main__":
    main()