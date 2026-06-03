#!/usr/bin/env python3
"""Create grid-independence plots from dcMetricsPlus CSV."""
from __future__ import annotations
import argparse
from pathlib import Path
import csv
import math

import matplotlib.pyplot as plt


def read_rows(path: Path):
    with path.open() as f:
        rows = list(csv.DictReader(f))
    def as_float(row, key):
        try:
            return float(row[key])
        except Exception:
            return math.nan
    rows.sort(key=lambda r: as_float(r, "hEff"), reverse=True)
    return rows, as_float


def plot(rows, as_float, xkey, ykey, ylabel, out):
    xs = [as_float(r, xkey) for r in rows]
    ys = [as_float(r, ykey) for r in rows]
    labels = [r.get("caseName", "") for r in rows]
    fig, ax = plt.subplots()
    ax.plot(xs, ys, marker="o")
    for x, y, lab in zip(xs, ys, labels):
        if math.isfinite(x) and math.isfinite(y):
            ax.annotate(lab, (x, y), textcoords="offset points", xytext=(5, 5))
    ax.set_xlabel(xkey)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("--outdir", type=Path, default=Path("grid_plots_plus"))
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    rows, as_float = read_rows(args.csv)
    items = [
        ("hEff", "TavgRackInlet", "Average rack inlet temperature [K]", "01_TavgRackInlet_vs_hEff.png"),
        ("hEff", "T95RackInlet", "95th percentile rack inlet temperature [K]", "02_T95RackInlet_vs_hEff.png"),
        ("hEff", "TmaxRackInlet", "Maximum rack inlet temperature [K]", "03_TmaxRackInlet_vs_hEff.png"),
        ("hEff", "TavgRoom", "Volume-average room temperature [K]", "04_TavgRoom_vs_hEff.png"),
        ("hEff", "returnOutletTmassFlowAvg", "Outflow-weighted return temperature [K]", "05_returnTmass_vs_hEff.png"),
        ("hEff", "roomHotspotVolumeFraction", "Room volume fraction T > threshold", "06_roomHotspotFraction_vs_hEff.png"),
        ("hEff", "rackInletHotspotFraction", "Rack inlet volume fraction T > threshold", "07_rackRiskFraction_vs_hEff.png"),
        ("hEff", "deltaP_supply_minus_return", "Delta p supply minus return", "08_deltaP_vs_hEff.png"),
        ("nCells", "runtimeSecondsParsed", "Runtime [s]", "09_runtime_vs_nCells.png"),
    ]
    for xkey, ykey, ylabel, name in items:
        if all(ykey not in r for r in rows):
            print(f"Skipping missing column {ykey}")
            continue
        plot(rows, as_float, xkey, ykey, ylabel, args.outdir / name)
    print(f"Wrote plots to {args.outdir}")


if __name__ == "__main__":
    main()
