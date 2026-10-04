#!/usr/bin/env python3

import argparse
import csv
import os


def read_rows(filename):
    with open(filename, newline="") as log_file:
        rows = list(csv.DictReader(log_file, delimiter=";"))
    if not rows:
        raise ValueError("le fichier ne contient aucune mesure: " + filename)
    return rows


def split_rows(rows):
    circuits = [[]]
    orange_active = False
    for row in rows:
        color = row.get("color", "").upper()
        is_orange = "ORANGE" in color
        if is_orange and not orange_active and circuits[-1]:
            circuits.append([])
        circuits[-1].append(row)
        orange_active = is_orange
    return [circuit for circuit in circuits if circuit]


def write_circuits(rows, source):
    circuits = split_rows(rows)
    stem, extension = os.path.splitext(source)
    fieldnames = list(rows[0].keys())
    for number, circuit in enumerate(circuits, 1):
        filename = "{0}_circuit_{1}{2}".format(stem, number, extension)
        with open(filename, "w", newline="") as log_file:
            writer = csv.DictWriter(log_file, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(circuit)
    return circuits


def make_svg(circuits, output):
    points = [
        (float(row["x_mm"]), float(row["y_mm"]))
        for circuit in circuits for row in circuit
    ]
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    width, height, margin = 1100, 800, 70
    scale = min(
        (width - 2 * margin) / max(max_x - min_x, 1),
        (height - 2 * margin) / max(max_y - min_y, 1),
    )

    def transform(row):
        x = margin + (float(row["x_mm"]) - min_x) * scale
        y = height - margin - (float(row["y_mm"]) - min_y) * scale
        return x, y

    colors = ("#d1495b", "#00798c", "#edae49", "#30638e", "#6a994e")
    lines = []
    for number, circuit in enumerate(circuits, 1):
        path = " ".join(
            ("M" if index == 0 else "L") + "{:.2f},{:.2f}".format(*transform(row))
            for index, row in enumerate(circuit)
        )
        color = colors[(number - 1) % len(colors)]
        lines.append('<path d="{}" fill="none" stroke="{}" stroke-width="3"/>'.format(path, color))
        start_x, start_y = transform(circuit[0])
        lines.append('<circle cx="{:.2f}" cy="{:.2f}" r="5" fill="{}"/>'.format(start_x, start_y, color))
        lines.append('<text x="{:.2f}" y="{:.2f}" font-size="14">Circuit {}</text>'.format(start_x + 8, start_y - 8, number))

    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" viewBox="0 0 {} {}">
<rect width="100%" height="100%" fill="#f7f4ef"/>
<text x="{}" y="32" font-family="sans-serif" font-size="22" font-weight="bold">Trajectoire EV3</text>
<text x="{}" y="54" font-family="sans-serif" font-size="13">{} mesures, {} circuit(s)</text>
<g font-family="sans-serif">{}</g>
<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="#555"/>
<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="#555"/>
</svg>
""".format(width, height, width, height, margin, margin, len(points), len(circuits), "\n".join(lines), margin, height - margin, width - margin, height - margin, margin, margin, margin, height - margin)
    with open(output, "w") as svg_file:
        svg_file.write(svg)


def main():
    parser = argparse.ArgumentParser(description="Découpe et trace les trajectoires EV3")
    parser.add_argument("log")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    rows = read_rows(args.log)
    circuits = write_circuits(rows, args.log)
    output = args.output or os.path.splitext(args.log)[0] + "_trajectory.svg"
    make_svg(circuits, output)
    print("{} circuit(s), {} mesure(s) -> {}".format(len(circuits), len(rows), output))


if __name__ == "__main__":
    main()