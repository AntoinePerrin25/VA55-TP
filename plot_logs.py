#!/usr/bin/env python3
"""Courbes TP2 (PC). Gains lus dans le CSV. Tous les *.csv par defaut.

  python3 plot_logs.py
  python3 plot_logs.py log_pid4125SEVERALCIRCLES.csv
"""

from __future__ import print_function

import argparse
import csv
import glob
import io
import math
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PARAM_COLS = ("DT", "KP", "KI", "KI_BLANC", "KD", "DELTA_MAX", "SPEED", "CONSIGNE")
PARAM_ORDER = (
    "commande",
    "DT",
    "TAU",
    "CONSIGNE",
    "SPEED",
    "SPEED_MIN",
    "E_PLEIN",
    "E_LENT",
    "KP",
    "KI",
    "KI_BLANC",
    "KD",
    "DELTA_MAX",
    "MAX_DDELTA",
)


def parse_meta(line):
    params = {}
    if not line.startswith("#meta"):
        return params
    for part in line.strip().lstrip("#").split(";"):
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        key = key.strip()
        val = val.strip()
        if key == "meta":
            continue
        try:
            params[key] = float(val) if "." in val else int(val)
        except ValueError:
            params[key] = val
    return params


def _num(row, *names):
    for name in names:
        if name in row and row[name] not in (None, ""):
            try:
                return float(row[name].replace(",", "."))
            except ValueError:
                pass
    return None


def load_csv(path):
    with open(path) as handle:
        raw = handle.read()
    lines = raw.splitlines()
    if not lines:
        return None
    first = lines[0]
    params = parse_meta(first)
    body = "\n".join(lines[1:] if params else lines) + "\n"
    reader = csv.DictReader(io.StringIO(body), delimiter=";")
    times, refl, err, cmd, speed, dist, zone = [], [], [], [], [], [], []
    row_params = []
    for row in reader:
        if not row:
            continue
        t = _num(row, "Temps (s)", "Temps")
        e = _num(row, "Erreur")
        if t is None or e is None:
            continue
        times.append(t)
        err.append(e)
        refl.append(_num(row, "Reflection") or 0.0)
        cmd.append(_num(row, "Commande (deg/s)", "Commande") or 0.0)
        speed.append(_num(row, "Vitesse (mm/s)", "Vitesse") or 0.0)
        dist.append(_num(row, "Distance (mm)", "Distance") or 0.0)
        zone.append((row.get("Zone") or "").strip())
        rp = {}
        for key in PARAM_COLS:
            val = _num(row, key)
            if val is not None:
                rp[key] = val
        row_params.append(rp)
    if not times:
        return None
    dts = [times[i] - times[i - 1] for i in range(1, len(times))]
    dts.sort()
    dt_med = dts[len(dts) // 2] if dts else 0.0
    inferred = []
    if "DT" not in params and dt_med > 0:
        params["DT"] = int(round(dt_med * 1000.0))
        params["TAU"] = round(dt_med, 3)
        inferred.append("DT/τ")
    if row_params and row_params[0]:
        for key, val in row_params[0].items():
            params.setdefault(key, val)
    if "SPEED" not in params and speed:
        params["SPEED"] = max(speed)
        inferred.append("SPEED")
    if "CONSIGNE" not in params:
        params["CONSIGNE"] = 50
        inferred.append("xc")
    vspan = max(speed) - min(speed) if speed else 0.0
    return {
        "t": times,
        "x": refl,
        "e": err,
        "u": cmd,
        "v": speed,
        "d": dist,
        "zone": zone,
        "row_params": row_params,
        "params": params,
        "meta_present": bool(parse_meta(first)),
        "inferred": inferred,
        "dt_med": dt_med,
        "v_varies": vspan > 5,
        "name": os.path.splitext(os.path.relpath(path, ROOT))[0],
        "path": path,
    }


def rmse(values):
    if not values:
        return 0.0
    return math.sqrt(sum(v * v for v in values) / float(len(values)))


def _window(t, series, t0, t1):
    out_t, out_y = [], []
    for i, ti in enumerate(t):
        if t0 <= ti <= t1:
            out_t.append(ti)
            out_y.append(series[i])
    return out_t, out_y


def abs_rate(t, y):
    if len(t) < 2 or t[-1] <= t[0]:
        return 0.0
    s = sum(abs(y[i] - y[i - 1]) for i in range(1, len(y)))
    return s / (t[-1] - t[0])


def zero_cross(y):
    n = 0
    for i in range(1, len(y)):
        if y[i - 1] * y[i] < 0:
            n += 1
    return n


def slice_stats(e, u, t, t0, t1):
    tw, ew = _window(t, e, t0, t1)
    _, uw = _window(t, u, t0, t1)
    n = float(len(ew)) or 1.0
    return {
        "n": len(ew),
        "t0": t0,
        "t1": t1,
        "rmse": rmse(ew),
        "mae": sum(abs(v) for v in ew) / n,
        "umean": sum(abs(v) for v in uw) / n if uw else 0.0,
        "dedt": abs_rate(tw, ew),
        "dudt": abs_rate(tw, uw),
        "zc": zero_cross(ew),
    }


def stats(run):
    e, u, v, t = run["e"], run["u"], run["v"], run["t"]
    params = run["params"]
    dmax = float(params.get("DELTA_MAX") or 100)
    n = float(len(e)) or 1.0
    sat = sum(1 for x in u if abs(x) >= 0.95 * dmax)
    big = sum(1 for x in e if abs(x) > 20)
    t0, t1 = t[0], t[-1]
    span = min(5.0, (t1 - t0) / 3.0)
    return {
        "parcours_s": t1 - t0,
        "dt_ms": run["dt_med"] * 1000.0,
        "rmse": rmse(e),
        "mae": sum(abs(x) for x in e) / n,
        "absmax": max(abs(x) for x in e),
        "pct_big": 100.0 * big / n,
        "pct_sat": 100.0 * sat / n,
        "vmean": sum(v) / n,
        "vmin": min(v),
        "vmax": max(v),
        "first": slice_stats(e, u, t, t0, t0 + span),
        "last": slice_stats(e, u, t, t1 - span, t1),
        "params": params,
        "meta_present": run["meta_present"],
        "inferred": run["inferred"],
    }


def diagnostic(run, s):
    p = s["params"]
    bits = []
    bits.append("PID = δ. x collé à xc = suivi lisse ; e = x−xc près de 0.")
    if s["mae"] < 10:
        bits.append("Suivi lisse (|e| moy. %.1f)." % s["mae"])
    elif s["mae"] < 18:
        bits.append("Un peu d’oscillation (|e| moy. %.1f)." % s["mae"])
    else:
        bits.append("Oscillations / sorties de voie (|e| moy. %.1f)." % s["mae"])
    if s["pct_sat"] > 15:
        bits.append("δ sature souvent (%.0f%%)." % s["pct_sat"])
    bits.append("parcours = %.1f s, dt = %.0f ms." % (s["parcours_s"], s["dt_ms"]))
    if not s["meta_present"] and "KP" not in p:
        bits.append("Pas de #meta (gains non figes dans ce fichier).")
    return " ".join(bits)


def params_txt(run):
    params = run["params"]
    bits = ["%s=%s" % (k, params[k]) for k in PARAM_ORDER if k in params]
    extra = []
    if not run["meta_present"] and not any("KP" in rp for rp in run["row_params"]):
        extra.append("sans #meta")
    if run["inferred"]:
        extra.append("infere: " + ",".join(run["inferred"]))
    txt = "  ".join(bits) if bits else "aucun parametre"
    if extra:
        txt += "  [" + " ; ".join(extra) + "]"
    return txt


def _poly(xs, ys, x0, y0, w, h, xmin, xmax, ymin, ymax):
    if xmax <= xmin:
        xmax = xmin + 1
    if ymax <= ymin:
        ymax = ymin + 1
    step = 1
    if len(xs) > 800:
        step = int(math.ceil(len(xs) / 800.0))
    pts = []
    for i in range(0, len(xs), step):
        x, y = xs[i], ys[i]
        px = x0 + (x - xmin) / (xmax - xmin) * w
        py = y0 + h - (y - ymin) / (ymax - ymin) * h
        pts.append("%.1f,%.1f" % (px, py))
    if (len(xs) - 1) % step != 0:
        x, y = xs[-1], ys[-1]
        px = x0 + (x - xmin) / (xmax - xmin) * w
        py = y0 + h - (y - ymin) / (ymax - ymin) * h
        pts.append("%.1f,%.1f" % (px, py))
    return " ".join(pts)


def _spans(run):
    slow = float(run["params"].get("SLOW_MM") or 450)
    t, d = run["t"], run["d"]
    out, start = [], None
    for i, dist in enumerate(d):
        close = dist < slow and dist < 2000
        if close and start is None:
            start = t[i]
        if (not close or i == len(d) - 1) and start is not None:
            out.append((start, t[i]))
            start = None
    return out


def svg_panel(run, series, ymin, ymax, color, x0, y0, w, h, hlines=(), extras=(), legend=()):
    t = run["t"]
    xmin, xmax = t[0], t[-1]
    parts = ["<g>"]
    for a, b in _spans(run):
        xa = x0 + (a - xmin) / (xmax - xmin) * w
        xb = x0 + (b - xmin) / (xmax - xmin) * w
        parts.append(
            '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#f5c6c6"/>'
            % (xa, y0, max(xb - xa, 1), h)
        )
    parts.append(
        '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#fafafa" stroke="#d4d4d8"/>'
        % (x0, y0, w, h)
    )
    for yv in hlines:
        py = y0 + h - (yv - ymin) / (ymax - ymin) * h
        if y0 <= py <= y0 + h:
            dash = "none" if yv == 0 else "6,4"
            parts.append(
                '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#a1a1aa" stroke-width="0.8" stroke-dasharray="%s"/>'
                % (x0, py, x0 + w, py, dash)
            )
            parts.append(
                '<text x="%.1f" y="%.1f" font-size="10" fill="#71717a" text-anchor="end">%s</text>'
                % (x0 - 6, py + 3, ("%g" % yv))
            )
    parts.append(
        '<polyline fill="none" stroke="%s" stroke-width="1.6" points="%s"/>'
        % (color, _poly(t, series, x0, y0, w, h, xmin, xmax, ymin, ymax))
    )
    for extra in extras:
        ys, ecol, dash, width = extra[0], extra[1], extra[2] if len(extra) > 2 else "none", extra[3] if len(extra) > 3 else 1.5
        dash_attr = ' stroke-dasharray="%s"' % dash if dash and dash != "none" else ""
        parts.append(
            '<polyline fill="none" stroke="%s" stroke-width="%s"%s points="%s"/>'
            % (ecol, width, dash_attr, _poly(t, ys, x0, y0, w, h, xmin, xmax, ymin, ymax))
        )
    lx = x0 + 8
    ly = y0 + 14
    for ecol, lab in legend:
        parts.append(
            '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="2"/>'
            % (lx, ly, lx + 16, ly, ecol)
        )
        parts.append(
            '<text x="%.1f" y="%.1f" font-size="11" fill="#3f3f46">%s</text>'
            % (lx + 20, ly + 4, lab)
        )
        lx += 110
    for frac, lab in ((0, "%.1f" % xmin), (0.5, "%.1f" % ((xmin + xmax) / 2)), (1, "%.1f" % xmax)):
        px = x0 + frac * w
        parts.append(
            '<text x="%.1f" y="%.1f" font-size="10" fill="#71717a" text-anchor="middle">%s</text>'
            % (px, y0 + h + 12, lab)
        )
    parts.append("</g>")
    return "".join(parts)


def _anchor(name):
    out = []
    for ch in name:
        if ch.isalnum():
            out.append(ch)
        else:
            out.append("-")
    return "".join(out)


def write_html(runs, path):
    pw, ph = 720, 125
    left, top = 88, 24
    gap = 30
    chunks = [
        "<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'>",
        "<title>TP2 commande laterale</title>",
        "<style>body{font:16px/1.45 ui-sans-serif,system-ui,sans-serif;margin:24px;color:#18181b;background:#fff}",
        "h1{font-size:1.25rem;font-weight:560} h2{font-size:1.05rem;font-weight:560;margin:1.6rem 0 .4rem}",
        "code{font:12px/1.4 ui-monospace,monospace} .params{background:#f4f4f5;padding:10px 12px;border-radius:8px;overflow-x:auto}",
        "table{border-collapse:collapse;font-size:14px;margin:.6rem 0 1rem} td,th{border:1px solid #e4e4e7;padding:6px 10px;text-align:left}",
        "a{color:#1d4ed8} .note{color:#3f3f46;max-width:78rem} .run{margin-bottom:2.4rem;padding-top:.4rem}",
        ".toc a{margin-right:12px;display:inline-block;margin-bottom:6px}</style></head><body>",
        "<h1>TP2 — commande laterale (PID)</h1>",
        "<p class='note'><b>e(t) = x(t) − x<sub>c</sub></b>. "
        "Le PID calcule <b>δ</b> (braquage, deg/s). "
        "Le graphe superposé montre la réflexion <code>x</code>, la consigne <code>x<sub>c</sub></code> "
        "et l’erreur <code>e</code> : suivi lisse si <code>x</code> colle <code>x<sub>c</sub></code> "
        "et <code>e</code> reste près de 0. Bande rose = obstacle. Gains dans le CSV.</p>",
        "<p class='note'>Sujet : log d’erreur + temps de parcours (droite 1 m, tapis).</p>",
    ]
    chunks.append("<p class='toc'>")
    for run in runs:
        chunks.append('<a href="#%s">%s</a>' % (_anchor(run["name"]), run["name"]))
    chunks.append("</p>")
    chunks.append("<h2>Evolution</h2><table><tr>")
    for h in ("run", "T (s)", "dt", "RMSE e", "|e|", "δ sat.", "KP", "KI", "KD", "SPEED"):
        chunks.append("<th>%s</th>" % h)
    chunks.append("</tr>")
    for run in runs:
        s = stats(run)
        p = run["params"]
        chunks.append(
            "<tr><td><a href='#%s'>%s</a></td><td>%.1f</td><td>%.0f ms</td>"
            "<td>%.1f</td><td>%.1f</td><td>%.0f%%</td>"
            "<td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
            % (
                _anchor(run["name"]),
                run["name"],
                s["parcours_s"],
                s["dt_ms"],
                s["rmse"],
                s["mae"],
                s["pct_sat"],
                p.get("KP", "—"),
                p.get("KI", "—"),
                p.get("KD", "—"),
                p.get("SPEED", "—"),
            )
        )
    chunks.append("</table>")
    for run in runs:
        s = stats(run)
        p = run["params"]
        dmax = float(p.get("DELTA_MAX") or 100)
        xc = float(p.get("CONSIGNE", 50))
        xc_series = [xc] * len(run["t"])
        overlay_h = 150
        panels = [
            {
                "lab": "x, xc, e",
                "ys": run["x"],
                "ymin": -50,
                "ymax": 100,
                "color": "#0f766e",
                "hlines": [0, xc],
                "extras": [
                    (xc_series, "#18181b", "7,4", 1.8),
                    (run["e"], "#1d4ed8", "none", 1.5),
                ],
                "legend": (
                    ("#0f766e", "x reflexion"),
                    ("#18181b", "xc consigne"),
                    ("#1d4ed8", "e = x−xc"),
                ),
                "h": overlay_h,
            },
            {
                "lab": "e = x − xc",
                "ys": run["e"],
                "ymin": -50,
                "ymax": 50,
                "color": "#1d4ed8",
                "hlines": [0, 20, -20],
                "extras": (),
                "legend": (),
                "h": ph,
            },
            {
                "lab": "δ PID (deg/s)",
                "ys": run["u"],
                "ymin": -dmax - 8,
                "ymax": dmax + 8,
                "color": "#b45309",
                "hlines": [0, dmax, -dmax],
                "extras": (),
                "legend": (),
                "h": ph,
            },
        ]
        svg_h = top
        for panel in panels:
            svg_h += panel["h"] + gap
        svg_w = left + pw + 16
        chunks.append('<div class="run" id="%s">' % _anchor(run["name"]))
        chunks.append(
            "<h2>%s — parcours <b>%.1f s</b></h2>" % (run["name"], s["parcours_s"])
        )
        chunks.append("<p class='params'><code>%s</code></p>" % params_txt(run))
        chunks.append("<p class='note'>%s</p>" % diagnostic(run, s))
        chunks.append(
            "<table><tr><th></th><th>RMSE e</th><th>|e|</th><th>|δ| moy.</th>"
            "<th>|e|&gt;20</th><th>sat. δ</th></tr>"
        )
        chunks.append(
            "<tr><td>run</td><td>%.1f</td><td>%.1f</td><td>%.1f</td><td>%.0f%%</td><td>%.0f%%</td></tr>"
            % (
                s["rmse"],
                s["mae"],
                (s["first"]["umean"] + s["last"]["umean"]) / 2.0,
                s["pct_big"],
                s["pct_sat"],
            )
        )
        chunks.append("</table>")
        svg = [
            "<svg viewBox='0 0 %d %d' width='100%%' role='img'>"
            % (svg_w, svg_h)
        ]
        y0 = top
        for panel in panels:
            svg.append(
                '<text x="%d" y="%d" font-size="12" text-anchor="end">%s</text>'
                % (left - 40, y0 + panel["h"] / 2, panel["lab"])
            )
            svg.append(
                svg_panel(
                    run,
                    panel["ys"],
                    panel["ymin"],
                    panel["ymax"],
                    panel["color"],
                    left,
                    y0,
                    pw,
                    panel["h"],
                    panel["hlines"],
                    panel["extras"],
                    panel["legend"],
                )
            )
            y0 += panel["h"] + gap
        svg.append("</svg>")
        chunks.append("".join(svg))
        chunks.append("</div>")
    chunks.append("</body></html>")
    with open(path, "w") as handle:
        handle.write("".join(chunks))


def discover_csvs():
    found = []
    for pattern in (
        os.path.join(ROOT, "*.csv"),
        os.path.join(ROOT, "*", "*.csv"),
    ):
        for path in glob.glob(pattern):
            ap = os.path.abspath(path)
            if ap not in found:
                found.append(ap)
    found.sort()
    return found


def expand_inputs(values):
    out = []
    for value in values:
        if any(ch in value for ch in "*?["):
            matches = glob.glob(value)
            if not matches:
                matches = glob.glob(os.path.join(ROOT, value))
            out.extend(os.path.abspath(p) for p in matches)
        elif os.path.isdir(value):
            out.extend(glob.glob(os.path.join(value, "*.csv")))
        else:
            out.append(os.path.abspath(value))
    seen = []
    for path in out:
        if path not in seen:
            seen.append(path)
    return seen


def main():
    parser = argparse.ArgumentParser(description="Graphes d'erreur TP2")
    parser.add_argument(
        "csv",
        nargs="*",
        help="CSV (defaut : tous les *.csv du dossier). Globs OK.",
    )
    args = parser.parse_args()
    paths = expand_inputs(args.csv) if args.csv else discover_csvs()
    paths = [p for p in paths if os.path.isfile(p) and p.lower().endswith(".csv")]
    if not paths:
        sys.exit("aucun CSV")
    runs = []
    skipped = []
    for path in paths:
        run = load_csv(path)
        if run is None:
            skipped.append(path)
        else:
            runs.append(run)
    if not runs:
        sys.exit("aucun log exploitable (colonne Erreur)")
    out = os.path.join(ROOT, "pid_plots.html")
    write_html(runs, out)
    print("sauve", out, "(%d runs)" % len(runs))
    for name in skipped:
        print("ignore", name)
    for run in runs:
        s = stats(run)
        print("---", run["name"], "---")
        print("  ", params_txt(run))
        print(
            "  parcours {:.1f}s  dt={:.0f}ms  RMSE e={:.1f}  |e|={:.1f}".format(
                s["parcours_s"],
                s["dt_ms"],
                s["rmse"],
                s["mae"],
            )
        )


if __name__ == "__main__":
    main()
