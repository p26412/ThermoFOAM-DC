#!/usr/bin/env python3
"""Compare two one-row dcMetricsPlus CSV files."""
from __future__ import annotations
import argparse, csv, math
from pathlib import Path

KEYS = [
    "TavgRackInlet", "T95RackInlet", "TmaxRackInlet",
    "TavgRoom", "T95Room", "TmaxRoom",
    "returnOutletTmassFlowAvg", "returnOutletTareaAvg",
    "roomHotspotVolumeFraction", "rackInletHotspotFraction",
    "deltaP_supply_minus_return",
]

def row(path: Path):
    with path.open() as f:
        return next(csv.DictReader(f))

def fval(r, k):
    try: return float(r[k])
    except Exception: return math.nan

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    args = ap.parse_args()
    ra, rb = row(args.a), row(args.b)
    print("metric,a,b,absoluteDifference,relativeDifferencePercent")
    for k in KEYS:
        a, b = fval(ra,k), fval(rb,k)
        if not math.isfinite(a) or not math.isfinite(b):
            continue
        diff = b-a
        rel = abs(diff)/max(abs(b),1e-300)*100
        print(f"{k},{a:.12g},{b:.12g},{diff:.12g},{rel:.6g}")
if __name__ == "__main__":
    main()
