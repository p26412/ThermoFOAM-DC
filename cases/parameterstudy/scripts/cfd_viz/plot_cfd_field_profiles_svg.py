#!/usr/bin/env python3
"""
Create SVG line plots for CFD profile CSV files written by PlotOverLine.

This script uses only the Python standard library. It reads profile CSV files and
creates line plots for:
  - Ux, Uy, Uz / u, v, w components
  - |U| velocity magnitude
  - T
  - p, p_rgh
  - k, epsilon, omega, nut, alphat, rho, mu, nu, Cp, h/he/e when present
  - any extra numeric scalar columns that are not obvious ParaView bookkeeping

Example:
  python3 scripts/cfd_viz/plot_cfd_field_profiles_svg.py results/plots/cfd_velocity/C00_baseline/profiles
"""

import argparse
import csv
import math
import re
from pathlib import Path


COMPONENT_STYLES = [
    ("#000000", ""),
    ("#555555", "9 5"),
    ("#999999", "3 4"),
    ("#333333", "13 5 3 5"),
]

KNOWN_SCALARS = [
    ("T", ["T"], "T [K]"),
    ("p_rgh", ["p_rgh", "prgh"], "p_rgh [Pa]"),
    ("p", ["p"], "p [Pa]"),
    ("k", ["k"], "k [m2/s2]"),
    ("epsilon", ["epsilon", "eps"], "epsilon [m2/s3]"),
    ("omega", ["omega"], "omega [1/s]"),
    ("nut", ["nut", "nu_t", "nuT"], "nut [m2/s]"),
    ("nuTilda", ["nuTilda", "nu_tilda"], "nuTilda [m2/s]"),
    ("alphat", ["alphat", "alpha_t"], "alphat [SI]"),
    ("rho", ["rho"], "rho [kg/m3]"),
    ("mu", ["mu"], "mu [Pa s]"),
    ("nu", ["nu"], "nu [m2/s]"),
    ("Cp", ["Cp", "cp"], "Cp [J/kg/K]"),
    ("h", ["h"], "h [J/kg]"),
    ("he", ["he"], "he [J/kg]"),
    ("e", ["e"], "e [J/kg]"),
]

BOOKKEEPING_PATTERNS = [
    r"^points[:_ ]?[012]$",
    r"^points_[012]$",
    r"^x$",
    r"^y$",
    r"^z$",
    r"^arc[_ ]?length$",
    r"^vtk",
    r"^block",
    r"^cell",
    r"^point",
    r"^id$",
    r"^ids$",
    r"^node",
    r"^process",
    r"^vtkvalidpointmask$",
    r"^vtkoriginal",
]


def norm(name):
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def is_bookkeeping_column(name):
    n = str(name).strip().lower().replace(" ", "_")
    compact = norm(name)
    for pattern in BOOKKEEPING_PATTERNS:
        if re.search(pattern, n) or re.search(pattern, compact):
            return True
    return False


def read_csv_rows(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader), list(reader.fieldnames or [])


def to_float(value):
    try:
        v = float(value)
        if math.isfinite(v):
            return v
    except Exception:
        pass
    return None


def find_column(fieldnames, candidates):
    exact = {name: name for name in fieldnames}
    normalized = {norm(name): name for name in fieldnames}
    for cand in candidates:
        if cand in exact:
            return exact[cand]
        key = norm(cand)
        if key in normalized:
            return normalized[key]
    return None


def find_component_columns(fieldnames):
    ux = find_column(fieldnames, ["Ux", "U_X", "U:0", "U_0", "U0", "u", "velocity:0", "velocity_0"])
    uy = find_column(fieldnames, ["Uy", "U_Y", "U:1", "U_1", "U1", "v", "velocity:1", "velocity_1"])
    uz = find_column(fieldnames, ["Uz", "U_Z", "U:2", "U_2", "U2", "w", "velocity:2", "velocity_2"])
    umag = find_column(fieldnames, ["Umag", "magU", "mag_U", "U_Magnitude", "Magnitude", "velocityMagnitude"])
    return ux, uy, uz, umag


def detect_axis_from_filename(path):
    name = Path(path).stem.lower()
    if "center_x" in name or name.endswith("_x") or "rack_height_x" in name or "floor_x" in name or "ceiling_x" in name:
        return "x"
    if "center_y" in name or name.endswith("_y"):
        return "y"
    if "center_z" in name or name.endswith("_z") or "vertical" in name:
        return "z"
    return "s"


def coordinate_column(fieldnames, axis_key):
    if axis_key == "x":
        col = find_column(fieldnames, ["Points:0", "Points_0", "Points0", "x", "X"])
        if col:
            return col, "x coordinate [m]"
    if axis_key == "y":
        col = find_column(fieldnames, ["Points:1", "Points_1", "Points1", "y", "Y"])
        if col:
            return col, "y coordinate [m]"
    if axis_key == "z":
        col = find_column(fieldnames, ["Points:2", "Points_2", "Points2", "z", "Z"])
        if col:
            return col, "z coordinate [m]"
    col = find_column(fieldnames, ["arc_length", "arc length", "arcLength", "Distance", "distance"])
    if col:
        return col, "distance along sample line [m]"
    # Last resort: use first point coordinate if it exists.
    col = find_column(fieldnames, ["Points:0", "Points_0", "Points0"])
    if col:
        return col, "x coordinate [m]"
    return None, "sample index [-]"


def collect_series(rows, x_col, y_col):
    pts = []
    for i, row in enumerate(rows):
        x = float(i) if x_col is None else to_float(row.get(x_col, ""))
        y = to_float(row.get(y_col, ""))
        if x is not None and y is not None:
            pts.append((x, y))
    pts.sort(key=lambda p: p[0])
    return pts


def computed_umag_series(rows, x_col, ux_col, uy_col, uz_col):
    pts = []
    for i, row in enumerate(rows):
        x = float(i) if x_col is None else to_float(row.get(x_col, ""))
        vals = [to_float(row.get(col, "")) for col in [ux_col, uy_col, uz_col] if col]
        vals = [v for v in vals if v is not None]
        if x is not None and vals:
            pts.append((x, math.sqrt(sum(v * v for v in vals))))
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
    all_x = []
    all_y = []
    for pts in series_dict.values():
        all_x.extend([p[0] for p in pts])
        all_y.extend([p[1] for p in pts])
    if not all_x or not all_y:
        return False

    xmin, xmax = nice_range(all_x)
    ymin, ymax = nice_range(all_y)

    left, right, top, bottom = 120, 55, 75, 115
    plot_w = width - left - right
    plot_h = height - top - bottom

    def sx(x):
        return left + (x - xmin) / (xmax - xmin) * plot_w

    def sy(y):
        return top + (ymax - y) / (ymax - ymin) * plot_h

    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    parts.append('<rect width="100%" height="100%" fill="white"/>')
    parts.append(f'<text x="{width/2:.1f}" y="36" text-anchor="middle" font-family="Arial" font-size="24" fill="black">{esc(title)}</text>')

    for t in ticks(xmin, xmax):
        x = sx(t)
        parts.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top+plot_h}" stroke="#dddddd" stroke-width="1"/>')
        parts.append(f'<text x="{x:.2f}" y="{top+plot_h+32}" text-anchor="middle" font-family="Arial" font-size="16" fill="black">{fmt_num(t)}</text>')
    for t in ticks(ymin, ymax):
        y = sy(t)
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left+plot_w}" y2="{y:.2f}" stroke="#dddddd" stroke-width="1"/>')
        parts.append(f'<text x="{left-16}" y="{y+5:.2f}" text-anchor="end" font-family="Arial" font-size="16" fill="black">{fmt_num(t)}</text>')

    parts.append(f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="black" stroke-width="2"/>')
    parts.append(f'<text x="{left+plot_w/2:.1f}" y="{height-35}" text-anchor="middle" font-family="Arial" font-size="20" fill="black">{esc(xlabel)}</text>')
    parts.append(f'<text x="34" y="{top+plot_h/2:.1f}" transform="rotate(-90 34 {top+plot_h/2:.1f})" text-anchor="middle" font-family="Arial" font-size="20" fill="black">{esc(ylabel)}</text>')

    legend_x = left + 22
    legend_y = top + 25
    for idx, (label, pts) in enumerate(series_dict.items()):
        if len(pts) < 2:
            continue
        color, dash = COMPONENT_STYLES[idx % len(COMPONENT_STYLES)]
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        coord_str = " ".join(f"{sx(x):.2f},{sy(y):.2f}" for x, y in pts)
        parts.append(f'<polyline points="{coord_str}" fill="none" stroke="{color}" stroke-width="3"{dash_attr}/>')
        ly = legend_y + 28 * idx
        parts.append(f'<line x1="{legend_x}" y1="{ly}" x2="{legend_x+36}" y2="{ly}" stroke="{color}" stroke-width="4"{dash_attr}/>')
        parts.append(f'<text x="{legend_x+46}" y="{ly+5}" font-family="Arial" font-size="18" fill="black">{esc(label)}</text>')

    parts.append('</svg>')
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(parts), encoding="utf-8")
    return True


def safe_filename(name):
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name)).strip("_")
    return s or "field"


def make_plots_for_csv(csv_path, out_dir, plot_extra_numeric=True):
    rows, fieldnames = read_csv_rows(csv_path)
    if not rows:
        return 0

    axis_key = detect_axis_from_filename(csv_path)
    x_col, xlabel = coordinate_column(fieldnames, axis_key)
    stem = Path(csv_path).stem
    made = 0

    ux_col, uy_col, uz_col, umag_col = find_component_columns(fieldnames)

    component_series = {}
    for label, col in [("Ux / u", ux_col), ("Uy / v", uy_col), ("Uz / w", uz_col)]:
        if col:
            pts = collect_series(rows, x_col, col)
            if pts:
                component_series[label] = pts

    if component_series:
        out_svg = Path(out_dir) / f"{stem}_U_components.svg"
        if svg_line_plot(component_series, xlabel, "velocity component [m/s]", f"{stem}: U, V, W components", out_svg):
            print(f"Wrote: {out_svg}")
            made += 1

    if umag_col:
        pts = collect_series(rows, x_col, umag_col)
    else:
        pts = computed_umag_series(rows, x_col, ux_col, uy_col, uz_col)
    if pts:
        out_svg = Path(out_dir) / f"{stem}_Umag.svg"
        if svg_line_plot({"|U|": pts}, xlabel, "|U| [m/s]", f"{stem}: velocity magnitude", out_svg):
            print(f"Wrote: {out_svg}")
            made += 1

    used_cols = set(c for c in [ux_col, uy_col, uz_col, umag_col, x_col] if c)

    for label, candidates, ylabel in KNOWN_SCALARS:
        col = find_column(fieldnames, candidates)
        if not col or col in used_cols:
            continue
        pts = collect_series(rows, x_col, col)
        if not pts:
            continue
        used_cols.add(col)
        out_svg = Path(out_dir) / f"{stem}_{safe_filename(label)}.svg"
        if svg_line_plot({label: pts}, xlabel, ylabel, f"{stem}: {label}", out_svg):
            print(f"Wrote: {out_svg}")
            made += 1

    if plot_extra_numeric:
        for col in fieldnames:
            if col in used_cols or is_bookkeeping_column(col):
                continue
            # Only plot columns that are mostly numeric and non-constant enough to matter.
            vals = [to_float(row.get(col, "")) for row in rows]
            vals = [v for v in vals if v is not None]
            if len(vals) < max(5, int(0.2 * len(rows))):
                continue
            if max(vals) - min(vals) < 1e-14:
                continue
            pts = collect_series(rows, x_col, col)
            if not pts:
                continue
            label = col
            out_svg = Path(out_dir) / f"{stem}_{safe_filename(col)}.svg"
            if svg_line_plot({label: pts}, xlabel, f"{label} [SI]", f"{stem}: {label}", out_svg):
                print(f"Wrote: {out_svg}")
                made += 1

    return made


def main():
    parser = argparse.ArgumentParser(description="Generate CFD line-profile SVG plots from PlotOverLine CSV files.")
    parser.add_argument("profiles_dir", help="Folder containing profile CSV files")
    parser.add_argument("--out-dir", default=None, help="Output folder. Default: PROFILES_DIR/line_plots")
    parser.add_argument("--no-extra-numeric", action="store_true", help="Only plot known CFD fields, not every extra numeric scalar")
    args = parser.parse_args()

    profiles_dir = Path(args.profiles_dir).resolve()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else profiles_dir / "line_plots"
    csv_files = sorted(p for p in profiles_dir.glob("*.csv") if p.is_file())
    if not csv_files:
        print(f"No profile CSV files found in {profiles_dir}")
        return 1

    made = 0
    for csv_path in csv_files:
        print(f"Reading: {csv_path}")
        made += make_plots_for_csv(csv_path, out_dir, plot_extra_numeric=not args.no_extra_numeric)

    print(f"CFD field line-profile SVG plots written: {made}")
    print(f"Output folder: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
