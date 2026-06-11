#!/usr/bin/env python3
"""
Create velocity-profile SVG plots from ParaView PlotOverLine CSV files.

This script uses only the Python standard library. No matplotlib, no NumPy,
no package drama, because apparently plotting one line should not require
performing surgery on your Python installation.

Input folder should contain:
  profile_center_x.csv
  profile_center_y.csv
  profile_center_z.csv

Output examples:
  Ux_vs_x_centerline.svg
  Uy_vs_y_centerline.svg
  Uz_vs_z_centerline.svg
  Umag_vs_z_centerline.svg
  velocity_components_vs_z_centerline.svg
"""

import argparse
import csv
import math
from pathlib import Path


COLORS = {
    "Ux": "#1f77b4",
    "Uy": "#d62728",
    "Uz": "#2ca02c",
    "Umag": "#111111",
}

PROFILE_CONFIG = {
    "x": {
        "csv": "profile_center_x.csv",
        "coord_candidates": ["Points:0", "Points_0", "Points0", "X", "x", "arc_length"],
        "xlabel": "x coordinate [m]",
        "suffix": "x_centerline",
        "recommended": ["Ux", "Umag"],
    },
    "y": {
        "csv": "profile_center_y.csv",
        "coord_candidates": ["Points:1", "Points_1", "Points1", "Y", "y", "arc_length"],
        "xlabel": "y coordinate [m]",
        "suffix": "y_centerline",
        "recommended": ["Uy", "Umag"],
    },
    "z": {
        "csv": "profile_center_z.csv",
        "coord_candidates": ["Points:2", "Points_2", "Points2", "Z", "z", "arc_length"],
        "xlabel": "z coordinate [m]",
        "suffix": "z_centerline",
        "recommended": ["Uz", "Umag"],
    },
}


def read_csv_rows(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def find_column(fieldnames, candidates):
    exact = {name: name for name in fieldnames}
    lower = {name.lower(): name for name in fieldnames}
    for cand in candidates:
        if cand in exact:
            return exact[cand]
        if cand.lower() in lower:
            return lower[cand.lower()]
    # Loose fallback: ParaView sometimes creates names like "U:0".
    for cand in candidates:
        cand_low = cand.lower().replace("_", "").replace(":", "")
        for name in fieldnames:
            name_low = name.lower().replace("_", "").replace(":", "")
            if name_low == cand_low:
                return name
    return None


def to_float(value):
    try:
        v = float(value)
        if math.isfinite(v):
            return v
    except Exception:
        pass
    return None


def collect_series(rows, x_col, y_col):
    pts = []
    for row in rows:
        x = to_float(row.get(x_col, ""))
        y = to_float(row.get(y_col, ""))
        if x is not None and y is not None:
            pts.append((x, y))
    pts.sort(key=lambda p: p[0])
    return pts


def nice_range(values):
    values = [v for v in values if math.isfinite(v)]
    if not values:
        return 0.0, 1.0
    vmin = min(values)
    vmax = max(values)
    if abs(vmax - vmin) < 1e-12:
        pad = max(abs(vmax) * 0.1, 1.0)
        return vmin - pad, vmax + pad
    pad = 0.08 * (vmax - vmin)
    return vmin - pad, vmax + pad


def ticks(vmin, vmax, n=5):
    if n <= 1:
        return [vmin]
    return [vmin + i * (vmax - vmin) / (n - 1) for i in range(n)]


def fmt_num(v):
    if abs(v) >= 1000 or (abs(v) > 0 and abs(v) < 0.001):
        return f"{v:.2e}"
    if abs(v) >= 100:
        return f"{v:.1f}"
    if abs(v) >= 10:
        return f"{v:.2f}"
    return f"{v:.3f}"


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_line_plot(series_dict, xlabel, ylabel, title, out_path, width=1200, height=820):
    # series_dict: label -> [(x, y), ...]
    all_x = []
    all_y = []
    for pts in series_dict.values():
        all_x.extend([p[0] for p in pts])
        all_y.extend([p[1] for p in pts])
    if not all_x or not all_y:
        return False

    xmin, xmax = nice_range(all_x)
    ymin, ymax = nice_range(all_y)

    left, right, top, bottom = 115, 55, 75, 115
    plot_w = width - left - right
    plot_h = height - top - bottom

    def sx(x):
        return left + (x - xmin) / (xmax - xmin) * plot_w

    def sy(y):
        return top + (ymax - y) / (ymax - ymin) * plot_h

    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    parts.append('<rect width="100%" height="100%" fill="white"/>')

    # Title
    parts.append(f'<text x="{width/2:.1f}" y="36" text-anchor="middle" font-family="Arial" font-size="24" fill="black">{esc(title)}</text>')

    # Grid and ticks
    for t in ticks(xmin, xmax):
        x = sx(t)
        parts.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top+plot_h}" stroke="#dddddd" stroke-width="1"/>')
        parts.append(f'<text x="{x:.2f}" y="{top+plot_h+32}" text-anchor="middle" font-family="Arial" font-size="16" fill="black">{fmt_num(t)}</text>')
    for t in ticks(ymin, ymax):
        y = sy(t)
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left+plot_w}" y2="{y:.2f}" stroke="#dddddd" stroke-width="1"/>')
        parts.append(f'<text x="{left-16}" y="{y+5:.2f}" text-anchor="end" font-family="Arial" font-size="16" fill="black">{fmt_num(t)}</text>')

    # Axes
    parts.append(f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="black" stroke-width="2"/>')
    parts.append(f'<text x="{left+plot_w/2:.1f}" y="{height-35}" text-anchor="middle" font-family="Arial" font-size="20" fill="black">{esc(xlabel)}</text>')
    parts.append(f'<text x="34" y="{top+plot_h/2:.1f}" transform="rotate(-90 34 {top+plot_h/2:.1f})" text-anchor="middle" font-family="Arial" font-size="20" fill="black">{esc(ylabel)}</text>')

    # Lines
    legend_x = left + 22
    legend_y = top + 25
    for idx, (label, pts) in enumerate(series_dict.items()):
        if len(pts) < 2:
            continue
        color = COLORS.get(label, "#444444")
        coord_str = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in pts)
        parts.append(f'<polyline points="{coord_str}" fill="none" stroke="{color}" stroke-width="3"/>')
        ly = legend_y + 28 * idx
        parts.append(f'<line x1="{legend_x}" y1="{ly}" x2="{legend_x+36}" y2="{ly}" stroke="{color}" stroke-width="4"/>')
        parts.append(f'<text x="{legend_x+46}" y="{ly+5}" font-family="Arial" font-size="18" fill="black">{esc(label)}</text>')

    parts.append('</svg>')
    Path(out_path).write_text("\n".join(parts), encoding="utf-8")
    return True


def make_plots_for_profile(folder, axis_key, cfg):
    csv_path = Path(folder) / cfg["csv"]
    if not csv_path.exists():
        print(f"WARNING: missing profile CSV: {csv_path}")
        return 0

    rows, fieldnames = read_csv_rows(csv_path)
    x_col = find_column(fieldnames, cfg["coord_candidates"])
    if x_col is None:
        print(f"WARNING: could not find coordinate column in {csv_path}")
        print("Columns:", fieldnames)
        return 0

    made = 0
    variable_candidates = {
        "Ux": ["Ux", "U_X", "U:0", "U_0"],
        "Uy": ["Uy", "U_Y", "U:1", "U_1"],
        "Uz": ["Uz", "U_Z", "U:2", "U_2"],
        "Umag": ["Umag", "magU", "U_Magnitude", "Magnitude"],
    }

    series = {}
    for var, candidates in variable_candidates.items():
        y_col = find_column(fieldnames, candidates)
        if y_col:
            pts = collect_series(rows, x_col, y_col)
            if pts:
                series[var] = pts

    # Single recommended plots, e.g. Ux vs x, Uy vs y, Uz vs z.
    for var in cfg["recommended"]:
        if var not in series:
            continue
        out_svg = Path(folder) / f"{var}_vs_{axis_key}_centerline.svg"
        ok = svg_line_plot(
            {var: series[var]},
            cfg["xlabel"],
            f"{var} [m/s]",
            f"{var} profile along {axis_key}-centerline",
            out_svg,
        )
        if ok:
            print(f"Wrote: {out_svg}")
            made += 1

    # Component comparison plot for this line.
    comp = {k: v for k, v in series.items() if k in ["Ux", "Uy", "Uz", "Umag"]}
    if comp:
        out_svg = Path(folder) / f"velocity_components_vs_{axis_key}_centerline.svg"
        ok = svg_line_plot(
            comp,
            cfg["xlabel"],
            "velocity [m/s]",
            f"Velocity components along {axis_key}-centerline",
            out_svg,
        )
        if ok:
            print(f"Wrote: {out_svg}")
            made += 1

    return made


def main():
    parser = argparse.ArgumentParser(description="Generate SVG velocity-profile plots from ParaView profile CSV files.")
    parser.add_argument("profiles_dir", help="Folder containing profile_center_x/y/z.csv")
    args = parser.parse_args()

    folder = Path(args.profiles_dir).resolve()
    made = 0
    for axis_key, cfg in PROFILE_CONFIG.items():
        made += make_plots_for_profile(folder, axis_key, cfg)
    print(f"SVG profile plots written: {made}")


if __name__ == "__main__":
    main()
