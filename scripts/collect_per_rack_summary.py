#!/usr/bin/env python3
"""Collect ThermoFOAM-DC per-rack dcMetricsPlus outputs into one v0.2 CSV.

Expected local layout:
  <cases-root>/<case>/postProcessing/dcMetricsPlus_perRack/<rack>/<time>/metrics.csv

The script writes:
  inputs/v02_per_rack_summary_user.csv

It is intentionally dependency-free: only the Python standard library is used.
"""
from __future__ import annotations

import argparse
import csv
import glob
import math
import statistics
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

RACK_ORDER = ["L1", "L2", "L3", "R1", "R2", "R3"]
PREFERRED_METRICS = [
    "TavgRackInlet",
    "T95RackInlet",
    "TmaxRackInlet",
    "rackInletHotspotFraction",
    "TavgRoom",
    "T95Room",
    "TmaxRoom",
    "roomHotspotVolumeFraction",
]


def to_float(value, default=float("nan")) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(str(value).strip())
    except Exception:
        return default


def fmt(x, ndigits: int = 6) -> str:
    x = to_float(x)
    if math.isnan(x):
        return ""
    if abs(x) >= 1000:
        return f"{x:.3f}"
    if abs(x) >= 100:
        return f"{x:.3f}"
    if abs(x) >= 10:
        return f"{x:.4f}"
    return f"{x:.6f}"


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: List[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def case_dir_for(cases_root: Path, case: Dict[str, str]) -> Path:
    folder = case.get("folder") or case.get("caseDir") or case.get("caseID") or ""
    path = cases_root / folder
    if path.exists():
        return path
    alt = cases_root / (case.get("caseID") or "")
    if alt.exists():
        return alt
    return path


def rack_power(case: Dict[str, str], rack_id: str) -> str:
    total = to_float(case.get("totalRackPowerW"))
    name = (case.get("caseName") or case.get("description") or "").lower()
    if "overloadedrack_l2" in name or "overloaded l2" in name or math.isclose(total, 23000.0):
        return "8000" if rack_id == "L2" else "3000"
    if math.isclose(total, 30000.0):
        return "5000"
    if math.isclose(total, 18000.0):
        return "3000"
    return ""


def numeric_keys(rows: Sequence[Dict[str, str]]) -> List[str]:
    keys: List[str] = []
    for key in PREFERRED_METRICS:
        if any(not math.isnan(to_float(r.get(key))) for r in rows):
            keys.append(key)
    for row in rows:
        for key, value in row.items():
            if key in keys or key in {"time", "caseID", "caseName", "rackID"}:
                continue
            if not math.isnan(to_float(value)):
                keys.append(key)
    return keys


def collect_rows(cases_root: Path, case_matrix: Sequence[Dict[str, str]], late_start: float) -> List[Dict[str, str]]:
    summary: List[Dict[str, str]] = []
    for case in case_matrix:
        cid = case.get("caseID", "")
        case_name = case.get("caseName", "")
        cdir = case_dir_for(cases_root, case)
        per_root = cdir / "postProcessing" / "dcMetricsPlus_perRack"
        if not per_root.exists():
            continue
        for rack in RACK_ORDER:
            rack_dir = per_root / rack
            if not rack_dir.exists():
                continue
            samples: List[Dict[str, str]] = []
            for path_str in sorted(glob.glob(str(rack_dir / "*" / "*.csv"))):
                path = Path(path_str)
                for row in read_csv(path):
                    t = to_float(row.get("time"))
                    if math.isnan(t):
                        t = to_float(path.parent.name)
                        row["time"] = fmt(t)
                    if t >= late_start:
                        samples.append(row)
            if not samples:
                continue
            samples.sort(key=lambda r: to_float(r.get("time")))
            out: Dict[str, str] = {
                "caseID": cid,
                "caseName": case_name,
                "folder": case.get("folder", ""),
                "rackID": rack,
                "rackPowerW": rack_power(case, rack),
                "nLateSamples": str(len(samples)),
                "lateTimeMin": fmt(min(to_float(r.get("time")) for r in samples)),
                "lateTimeMax": fmt(max(to_float(r.get("time")) for r in samples)),
            }
            for key in numeric_keys(samples):
                vals = [to_float(r.get(key)) for r in samples if not math.isnan(to_float(r.get(key)))]
                if not vals:
                    continue
                out[key + "_mean"] = fmt(statistics.mean(vals))
                out[key + "_std"] = fmt(statistics.stdev(vals) if len(vals) > 1 else 0.0)
                out[key + "_min"] = fmt(min(vals))
                out[key + "_max"] = fmt(max(vals))
                out[key + "_final"] = fmt(to_float(samples[-1].get(key)))
            summary.append(out)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect per-rack ThermoFOAM-DC v0.2 metrics into one CSV.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--cases-root", type=Path, default=None)
    parser.add_argument("--late-start", type=float, default=4000.0)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    root = args.project_root.resolve()
    cases_root = args.cases_root.resolve() if args.cases_root else (root / "cases" / "parameterstudy").resolve()
    out_path = args.out.resolve() if args.out else (root / "inputs" / "v02_per_rack_summary_user.csv").resolve()
    case_matrix = read_csv(root / "metadata" / "v02_case_matrix.csv")
    if not case_matrix:
        raise SystemExit("Missing metadata/v02_case_matrix.csv")
    rows = collect_rows(cases_root, case_matrix, args.late_start)
    if not rows:
        print("No per-rack dcMetricsPlus files found. Searched:", cases_root)
        return
    write_csv(out_path, rows)
    print(f"Wrote {len(rows)} per-rack rows to {out_path}")


if __name__ == "__main__":
    main()
