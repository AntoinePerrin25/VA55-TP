#!/usr/bin/env python3
"""Figures du rapport : erreur et commande, termes PID en couleurs.

  python3 slidesTP1/plot_rapport.py
"""

import csv
import io
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plots")


def axes_style(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.axhline(0, color="black", linewidth=0.6, linestyle=(0, (4, 3)))


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=140, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print(name)


def pair(t, e, u, name, mark=None):
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(11.6, 5.6), sharex=True, gridspec_kw={"hspace": 0.18}
    )
    top.plot(t, e, color="black", linewidth=0.9)
    axes_style(top)
    top.set_ylabel("e")
    top.set_ylim(-50, 50)
    bottom.plot(t, u, color="black", linewidth=0.9)
    axes_style(bottom)
    bottom.set_ylabel("δ")
    bottom.set_xlabel("temps (s)")
    bottom.set_xlim(0, t[-1])
    if mark is not None:
        for ax in (top, bottom):
            ax.axvline(mark, color="black", linewidth=0.7, linestyle=(0, (2, 2)))
        top.text(mark + 0.12, 38, "1 m", fontsize=14, color="black")
    save(fig, name)


def main():
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 15,
        "axes.labelsize": 16,
        "axes.edgecolor": "black",
        "axes.labelcolor": "black",
        "xtick.color": "black",
        "ytick.color": "black",
        "text.color": "black",
        "axes.linewidth": 0.9,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    })

    rows = list(csv.DictReader(open(os.path.join(ROOT, "logsPIDbetter/bang_bang.csv"))))
    t0 = float(rows[0]["time_ms"]) / 1000.0
    pair(
        [float(r["time_ms"]) / 1000.0 - t0 for r in rows],
        [float(r["error"]) for r in rows],
        [float(r["steering"]) for r in rows],
        "bangbang.png",
    )

    raw = open(os.path.join(ROOT, "logsTP1/log_pid_STRAIGHT.csv")).read().splitlines()[1:]
    rd = list(csv.DictReader(io.StringIO("\n".join(raw) + "\n"), delimiter=";"))
    t0 = float(rd[0]["Temps (s)"])
    pair(
        [float(r["Temps (s)"]) - t0 for r in rd],
        [float(r["Erreur"]) for r in rd],
        [float(r["Commande (deg/s)"]) for r in rd],
        "droite.png",
        mark=1000.0 / 155.0,
    )

    rows = list(csv.DictReader(open(os.path.join(ROOT, "logsPIDbetter/suivi_pid_tapis_spir.csv"))))
    t0 = float(rows[0]["time_ms"]) / 1000.0
    pair(
        [float(r["time_ms"]) / 1000.0 - t0 for r in rows],
        [float(r["error"]) for r in rows],
        [float(r["steering"]) for r in rows],
        "tapis.png",
    )
    termes(rows, t0, 8.6, 12.6)


def termes(rows, t0, t_start, t_end):
    kp, ki, kd = 2.0, 1.70, 0.035
    t, e, p, i_term, d_term, u = [], [], [], [], [], []
    for row in rows:
        time = float(row["time_ms"]) / 1000.0 - t0
        if time < t_start or time > t_end:
            continue
        error = float(row["error"])
        t.append(time)
        e.append(error)
        p.append(kp * error)
        i_term.append(ki * float(row["integral"]))
        d_term.append(kd * float(row["derivative"]))
        u.append(float(row["steering"]))
    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(11.4, 5.9), sharex=True, gridspec_kw={"hspace": 0.28}
    )
    top.plot(t, e, color="black", linewidth=1.3)
    axes_style(top)
    top.set_ylabel("e")
    top.set_ylim(-50, 50)
    bottom.plot(t, p, color="#0072B2", linewidth=1.8, label="P")
    bottom.plot(t, i_term, color="#D55E00", linewidth=1.8, linestyle=(0, (6, 2)), label="I")
    bottom.plot(t, d_term, color="#009E73", linewidth=1.9, linestyle=(0, (1, 1.5)), label="D")
    bottom.plot(t, u, color="#CC79A7", linewidth=2.0, linestyle=(0, (5, 1.2, 1, 1.2)), label="δ")
    axes_style(bottom)
    bottom.set_ylabel("P, I, D, δ")
    bottom.set_xlabel("temps (s)")
    bottom.set_xlim(t[0], t[-1])
    bottom.legend(
        frameon=False, ncol=4, loc="lower center",
        bbox_to_anchor=(0.5, 1.02), fontsize=13,
    )
    save(fig, "pid_termes.png")


if __name__ == "__main__":
    main()
