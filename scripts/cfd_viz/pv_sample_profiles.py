#!/usr/bin/env pvpython
"""
Sample CFD line profiles from an OpenFOAM case using ParaView.

Example:
    pvpython scripts/cfd_viz/pv_sample_profiles.py --case C00_baseline --time 8000

Outputs CSV files to results/cfd_profiles/<case>.
"""

import argparse
import os
import sys

try:
    from paraview.simple import OpenFOAMReader, CellDatatoPointData, PlotOverLine, SaveData  # type: ignore
except Exception as exc:
    print("ERROR: Run with pvpython, not normal python3.", file=sys.stderr)
    print(str(exc), file=sys.stderr)
    sys.exit(2)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--case", required=True)
    p.add_argument("--time", default="latest")
    p.add_argument("--outdir", default=None)
    p.add_argument("--domain", nargs=3, type=float, default=[7.0, 5.0, 3.0])
    p.add_argument("--rack-height-z", type=float, default=1.5)
    p.add_argument("--npts", type=int, default=250)
    return p.parse_args()


def ensure_foam_file(case_dir):
    name = os.path.basename(os.path.abspath(case_dir))
    foam = os.path.join(case_dir, name + ".foam")
    if not os.path.exists(foam):
        open(foam, "a").close()
    return foam


def time_value(reader, requested):
    reader.UpdatePipeline()
    vals = []
    try:
        vals = list(reader.TimestepValues)
    except Exception:
        vals = []
    if not vals:
        return None
    if str(requested).lower() == "latest":
        return max(vals)
    target = float(requested)
    return min(vals, key=lambda x: abs(float(x) - target))


def sample_line(src, name, p1, p2, npts, outdir, t):
    line = PlotOverLine(Input=src)
    try:
        line.Source.Point1 = p1
        line.Source.Point2 = p2
        line.Source.Resolution = npts
    except Exception:
        pass
    line.UpdatePipeline(t)
    out = os.path.join(outdir, name + ".csv")
    SaveData(out, proxy=line)
    print("wrote", out)


def main():
    args = parse_args()
    case_dir = os.path.abspath(args.case)
    case_name = os.path.basename(case_dir)
    outdir = os.path.abspath(args.outdir or os.path.join("results", "cfd_profiles", case_name))
    os.makedirs(outdir, exist_ok=True)

    lx, ly, lz = args.domain
    foam = ensure_foam_file(case_dir)
    r = OpenFOAMReader(FileName=foam)
    try:
        r.SkipZeroTime = 1
    except Exception:
        pass
    t = time_value(r, args.time)
    print("Using time:", t)

    pt = CellDatatoPointData(Input=r)
    try:
        pt.PassCellData = 1
    except Exception:
        pass
    pt.UpdatePipeline(t)

    z = args.rack_height_z
    lines = {
        "vertical_centerline_room_T_U": ([lx / 2, ly / 2, 0.02], [lx / 2, ly / 2, lz - 0.02]),
        "horizontal_x_rack_height_center_y_T_U": ([0.02, ly / 2, z], [lx - 0.02, ly / 2, z]),
        "horizontal_y_rack_height_center_x_T_U": ([lx / 2, 0.02, z], [lx / 2, ly - 0.02, z]),
        "supply_to_return_diagonal_T_U": ([0.15 * lx, 0.15 * ly, 0.05], [0.85 * lx, 0.85 * ly, lz - 0.05]),
        "near_floor_centerline_x_T_U": ([0.02, ly / 2, 0.15], [lx - 0.02, ly / 2, 0.15]),
        "near_ceiling_centerline_x_T_U": ([0.02, ly / 2, lz - 0.15], [lx - 0.02, ly / 2, lz - 0.15]),
    }

    for name, (p1, p2) in lines.items():
        sample_line(pt, name, p1, p2, args.npts, outdir, t)

    print("Done. Profile CSV files written to", outdir)


if __name__ == "__main__":
    main()
