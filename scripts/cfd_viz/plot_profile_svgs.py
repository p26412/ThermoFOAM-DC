#!/usr/bin/env python3
"""
Create SVG line/profile plots from ParaView PlotOverLine CSV outputs.
No numpy, no pandas, no matplotlib. Humanity may yet survive.
"""

import argparse
import csv
import glob
import math
import os
from typing import Dict, List, Tuple


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", default="results/cfd_profiles")
    p.add_argument("--outdir", default="results/cfd_figures/profiles")
    return p.parse_args()


def to_float(v):
    try:
        return float(v)
    except Exception:
        return float("nan")


def read_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return rows


def find_col(header, names):
    norm = {h.lower().replace(" ", "").replace("_", ""): h for h in header}
    for n in names:
        key = n.lower().replace(" ", "").replace("_", "")
        if key in norm:
            return norm[key]
    return None


def get_x(rows):
    if not rows:
        return [], "distance along sample line [m]"
    header = list(rows[0].keys())
    arc = find_col(header, ["arc_length", "arc length", "arc_length"])
    if arc:
        return [to_float(r[arc]) for r in rows], "distance along sample line [m]"
    px = find_col(header, ["Points:0", "Points_0", "Points0", "Points:0"])
    py = find_col(header, ["Points:1", "Points_1", "Points1"])
    pz = find_col(header, ["Points:2", "Points_2", "Points2"])
    if px and py and pz:
        pts = [(to_float(r[px]), to_float(r[py]), to_float(r[pz])) for r in rows]
        x = [0.0]
        for i in range(1, len(pts)):
            dx = pts[i][0] - pts[i - 1][0]
            dy = pts[i][1] - pts[i - 1][1]
            dz = pts[i][2] - pts[i - 1][2]
            x.append(x[-1] + math.sqrt(dx * dx + dy * dy + dz * dz))
        return x, "distance along sample line [m]"
    return list(range(len(rows))), "sample index [-]"


def get_series(rows, col):
    return [to_float(r[col]) for r in rows]


def finite_xy(x, y):
    outx, outy = [], []
    for a, b in zip(x, y):
        if math.isfinite(a) and math.isfinite(b):
            outx.append(a)
            outy.append(b)
    return outx, outy


def nice_range(vals):
    vals = [v for v in vals if math.isfinite(v)]
    if not vals:
        return 0.0, 1.0
    mn, mx = min(vals), max(vals)
    if mn == mx:
        pad = max(1.0, abs(mn) * 0.05)
        return mn - pad, mx + pad
    pad = 0.07 * (mx - mn)
    return mn - pad, mx + pad


def svg_line_plot(path, title, xlabel, ylabel, series: List[Tuple[str, List[float], List[float]]]):
    width, height = 1100, 720
    left, right, top, bottom = 110, 40, 70, 95
    plot_w = width - left - right
    plot_h = height - top - bottom
    allx = [v for _, x, _ in series for v in x]
    ally = [v for _, _, y in series for v in y]
    xmin, xmax = nice_range(allx)
    ymin, ymax = nice_range(ally)

    def sx(v):
        return left + (v - xmin) / (xmax - xmin) * plot_w

    def sy(v):
        return top + plot_h - (v - ymin) / (ymax - ymin) * plot_h

    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    styles = [
        "stroke:#000000;stroke-width:2.3;fill:none",
        "stroke:#555555;stroke-width:2.3;fill:none;stroke-dasharray:9 5",
        "stroke:#999999;stroke-width:2.3;fill:none;stroke-dasharray:3 4",
        "stroke:#333333;stroke-width:1.9;fill:none;stroke-dasharray:13 5 3 5",
    ]

    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    parts.append('<rect width="100%" height="100%" fill="white"/>')
    parts.append(f'<text x="{width/2}" y="32" font-family="Arial" font-size="24" text-anchor="middle">{esc(title)}</text>')

    # grid and ticks
    for i in range(6):
        xv = xmin + (xmax - xmin) * i / 5
        xp = sx(xv)
        parts.append(f'<line x1="{xp:.1f}" y1="{top}" x2="{xp:.1f}" y2="{top+plot_h}" stroke="#e6e6e6"/>')
        parts.append(f'<text x="{xp:.1f}" y="{top+plot_h+28}" font-family="Arial" font-size="15" text-anchor="middle">{xv:.3g}</text>')
    for i in range(6):
        yv = ymin + (ymax - ymin) * i / 5
        yp = sy(yv)
        parts.append(f'<line x1="{left}" y1="{yp:.1f}" x2="{left+plot_w}" y2="{yp:.1f}" stroke="#e6e6e6"/>')
        parts.append(f'<text x="{left-14}" y="{yp+5:.1f}" font-family="Arial" font-size="15" text-anchor="end">{yv:.3g}</text>')

    # axes
    parts.append(f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="black" stroke-width="1.5"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="black" stroke-width="1.5"/>')
    parts.append(f'<text x="{left+plot_w/2}" y="{height-35}" font-family="Arial" font-size="20" text-anchor="middle">{esc(xlabel)}</text>')
    parts.append(f'<text x="30" y="{top+plot_h/2}" transform="rotate(-90 30 {top+plot_h/2})" font-family="Arial" font-size="20" text-anchor="middle">{esc(ylabel)}</text>')

    for idx, (label, x, y) in enumerate(series):
        x, y = finite_xy(x, y)
        if len(x) < 2:
            continue
        d = " ".join([f"{sx(a):.2f},{sy(b):.2f}" for a, b in zip(x, y)])
        parts.append(f'<polyline points="{d}" style="{styles[idx % len(styles)]}"/>')
        lx = left + plot_w - 230
        ly = top + 25 + 25 * idx
        parts.append(f'<line x1="{lx}" y1="{ly}" x2="{lx+38}" y2="{ly}" style="{styles[idx % len(styles)]}"/>')
        parts.append(f'<text x="{lx+48}" y="{ly+5}" font-family="Arial" font-size="16">{esc(label)}</text>')

    parts.append('</svg>')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(parts))
    print("wrote", path)


def make_plots_for_csv(path, outdir):
    rows = read_csv(path)
    if not rows:
        return
    header = list(rows[0].keys())
    x, xlabel = get_x(rows)
    stem = os.path.splitext(os.path.basename(path))[0]
    case = os.path.basename(os.path.dirname(path))
    prefix = os.path.join(outdir, case + "_" + stem)

    # Temperature
    tcol = find_col(header, ["T"])
    if tcol:
        y = get_series(rows, tcol)
        svg_line_plot(prefix + "_T.svg", f"{case}: {stem} - temperature", xlabel, "T [K]", [("T", x, y)])

    # Pressure
    pcol = find_col(header, ["p_rgh", "p"])
    if pcol:
        y = get_series(rows, pcol)
        svg_line_plot(prefix + "_pressure.svg", f"{case}: {stem} - pressure field", xlabel, f"{pcol} [SI]", [(pcol, x, y)])

    # U components and magnitude
    ux = find_col(header, ["U:0", "U_0", "U0", "U_X"])
    uy = find_col(header, ["U:1", "U_1", "U1", "U_Y"])
    uz = find_col(header, ["U:2", "U_2", "U2", "U_Z"])
    series = []
    if ux:
        series.append(("Ux", x, get_series(rows, ux)))
    if uy:
        series.append(("Uy", x, get_series(rows, uy)))
    if uz:
        series.append(("Uz", x, get_series(rows, uz)))
    if series:
        svg_line_plot(prefix + "_U_components.svg", f"{case}: {stem} - velocity components", xlabel, "velocity component [m/s]", series)
        mag = []
        for i in range(len(x)):
            vals = []
            for col in (ux, uy, uz):
                if col:
                    vals.append(to_float(rows[i][col]))
            if vals:
                mag.append(math.sqrt(sum(v * v for v in vals if math.isfinite(v))))
            else:
                mag.append(float("nan"))
        svg_line_plot(prefix + "_magU.svg", f"{case}: {stem} - velocity magnitude", xlabel, "|U| [m/s]", [("|U|", x, mag)])

    # Turbulence scalars
    for fld, ylabel in [("k", "k [m2/s2]"), ("epsilon", "epsilon [m2/s3]"), ("omega", "omega [1/s]"), ("nut", "nut [m2/s]")]:
        col = find_col(header, [fld])
        if col:
            svg_line_plot(prefix + f"_{fld}.svg", f"{case}: {stem} - {fld}", xlabel, ylabel, [(fld, x, get_series(rows, col))])


def main():
    args = parse_args()
    files = sorted(glob.glob(os.path.join(args.input_dir, "**", "*.csv"), recursive=True))
    if not files:
        print("No CSV profile files found in", args.input_dir)
        return
    for path in files:
        make_plots_for_csv(path, args.outdir)


if __name__ == "__main__":
    main()
