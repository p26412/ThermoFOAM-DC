#!/usr/bin/env python3
"""Collect dcMetricsPlus CSV files from multiple cases into one CSV."""
from __future__ import annotations
import argparse
import csv
import re
from pathlib import Path
from typing import Optional


def find_metrics(case: Path) -> Optional[Path]:
    candidates = sorted((case / "postProcessing" / "dcMetricsPlus").glob("*/metrics.csv"), key=lambda p: float(p.parent.name) if p.parent.name.replace('.','',1).isdigit() else -1)
    return candidates[-1] if candidates else None


def parse_runtime(case: Path) -> str:
    logs = list(case.glob("log.foamRun*")) + list(case.glob("log.continue*"))
    total = 0.0
    found = False
    pattern = re.compile(r"ExecutionTime\s*=\s*([0-9.eE+-]+)\s*s")
    for log in logs:
        try:
            text = log.read_text(errors="ignore")
        except Exception:
            continue
        vals = [float(m.group(1)) for m in pattern.finditer(text)]
        if vals:
            # use the last execution time in each log segment
            total += vals[-1]
            found = True
    return f"{total:.6g}" if found else ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="+", type=Path)
    ap.add_argument("--output", type=Path, default=Path("grid_metrics_plus.csv"))
    args = ap.parse_args()

    rows = []
    fieldnames = []
    for case in args.cases:
        metrics = find_metrics(case)
        if not metrics:
            print(f"WARNING: no metrics found in {case}")
            continue
        with metrics.open() as f:
            reader = csv.DictReader(f)
            row = next(reader)
        row["caseName"] = case.name
        row["caseDir"] = str(case.resolve())
        row["runtimeSecondsParsed"] = parse_runtime(case)
        rows.append(row)
        for k in row.keys():
            if k not in fieldnames:
                fieldnames.append(k)

    # Put useful identifiers first
    preferred = ["caseName", "caseDir", "time", "nCells", "hEff", "runtimeSecondsParsed"]
    fieldnames = preferred + [k for k in fieldnames if k not in preferred]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
