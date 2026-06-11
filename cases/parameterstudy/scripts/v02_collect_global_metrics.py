#!/usr/bin/env python3
"""
Collect global dcMetricsPlus outputs for v0.2 parameter cases.

This version is deliberately tolerant of folder names and time folders:
- caseDir may be C00, C00_baseline, or any explicit path in v02_case_matrix.csv
- metrics are discovered from postProcessing/dcMetricsPlus/*/metrics.csv
- only samples within --start-time and --end-time are used for late averages
"""

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOM_VOLUME = 105.0              # m3
SUPPLY_AREA = 3.0 * 0.8 * 0.6    # m2
RHO_REF = 1.2                    # kg/m3
CP_AIR = 1005.0                  # J/kg/K

BASE_METRICS = [
    "TavgRackInlet",
    "T95RackInlet",
    "TmaxRackInlet",
    "TavgRoom",
    "T95Room",
    "TmaxRoom",
    "roomHotspotVolumeFraction",
    "rackInletHotspotFraction",
    "returnOutletTareaAvg",
    "returnOutletTmassFlowAvg",
    "returnOutletOutflowFlux",
    "deltaP_supply_minus_return",
]


def parse_float_time(name: str):
    try:
        return float(name)
    except ValueError:
        return None


def resolve_case_dir(case_row, base_dir: Path) -> Path:
    """Resolve case directory robustly from caseDir/caseID/caseName."""
    candidates = []

    for key in ["caseDir", "caseID", "caseName"]:
        value = str(case_row.get(key, "")).strip()
        if value and value.lower() != "nan":
            p = Path(value)
            candidates.append(p if p.is_absolute() else base_dir / p)

    for p in candidates:
        if p.exists() and p.is_dir():
            return p

    # Try prefix match such as C00_baseline when caseDir is C00, or C00 when caseDir is C00_baseline
    case_id = str(case_row.get("caseID", "")).strip()
    if case_id:
        matches = sorted(base_dir.glob(f"{case_id}*"))
        matches = [m for m in matches if m.is_dir()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            print(f"WARNING: multiple folders match {case_id}: {[str(m) for m in matches]}", file=sys.stderr)

    raise FileNotFoundError(
        f"Cannot resolve case directory for caseID={case_row.get('caseID')} caseDir={case_row.get('caseDir')}. "
        f"Check results/tables/v02_case_matrix.csv."
    )


def discover_metrics_files(case_dir: Path, start_time: float, end_time: float):
    root = case_dir / "postProcessing" / "dcMetricsPlus"
    if not root.exists():
        return []

    files = []
    for metrics_path in root.glob("*/metrics.csv"):
        folder_time = parse_float_time(metrics_path.parent.name)
        if folder_time is None:
            continue
        if start_time <= folder_time <= end_time:
            files.append((folder_time, metrics_path))

    return sorted(files, key=lambda x: x[0])


def read_one_metrics_file(case_row, case_dir: Path, folder_time: float, metrics_path: Path):
    df = pd.read_csv(metrics_path)
    if df.empty:
        print(f"WARNING: empty {metrics_path}", file=sys.stderr)
        return None

    row = df.iloc[0].to_dict()

    # Prefer CSV time column when available; folder time otherwise.
    row_time = row.get("time", folder_time)
    try:
        row_time = float(row_time)
    except Exception:
        row_time = float(folder_time)

    row["caseID"] = str(case_row["caseID"])
    row["caseName"] = str(case_row["caseName"])
    row["caseDir"] = str(case_dir)
    row["timeSample"] = row_time

    row["Usupply"] = float(case_row["Usupply"])
    row["Tsupply"] = float(case_row["Tsupply"])
    row["totalRackPowerW"] = float(case_row["totalRackPowerW"])
    row["expectedSupplyFlow"] = SUPPLY_AREA * row["Usupply"]

    return row


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Required columns check with a useful message instead of a pandas tantrum.
    required = [
        "TavgRackInlet", "T95RackInlet", "TmaxRackInlet",
        "TavgRoom", "T95Room", "TmaxRoom",
        "returnOutletTmassFlowAvg", "returnOutletOutflowFlux",
        "deltaP_supply_minus_return",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns in dcMetricsPlus CSV: {missing}")

    df["TavgRackRise"] = df["TavgRackInlet"] - df["Tsupply"]
    df["T95RackRise"] = df["T95RackInlet"] - df["Tsupply"]
    df["TmaxRackRise"] = df["TmaxRackInlet"] - df["Tsupply"]

    df["TavgRoomRise"] = df["TavgRoom"] - df["Tsupply"]
    df["T95RoomRise"] = df["T95Room"] - df["Tsupply"]
    df["TmaxRoomRise"] = df["TmaxRoom"] - df["Tsupply"]

    df["returnTempRise"] = df["returnOutletTmassFlowAvg"] - df["Tsupply"]

    df["flowBalanceErrorPercent"] = (
        100.0 * (df["returnOutletOutflowFlux"] - df["expectedSupplyFlow"]).abs()
        / df["expectedSupplyFlow"]
    )

    df["pressurePowerProxy"] = (
        df["deltaP_supply_minus_return"] * df["returnOutletOutflowFlux"]
    )

    df["airChangesPerHour"] = df["returnOutletOutflowFlux"] * 3600.0 / ROOM_VOLUME

    df["estimatedHeatRemovedW"] = (
        RHO_REF * CP_AIR * df["returnOutletOutflowFlux"]
        * (df["returnOutletTmassFlowAvg"] - df["Tsupply"])
    )

    df["heatBalanceErrorPercent"] = (
        100.0 * (df["estimatedHeatRemovedW"] - df["totalRackPowerW"]).abs()
        / df["totalRackPowerW"]
    )

    return df


def summarize_case(group: pd.DataFrame) -> pd.Series:
    identity_cols = [
        "caseID", "caseName", "caseDir", "Usupply", "Tsupply",
        "totalRackPowerW", "expectedSupplyFlow",
    ]

    metric_cols = BASE_METRICS + [
        "TavgRackRise", "T95RackRise", "TmaxRackRise",
        "TavgRoomRise", "T95RoomRise", "TmaxRoomRise",
        "returnTempRise", "flowBalanceErrorPercent", "pressurePowerProxy",
        "airChangesPerHour", "estimatedHeatRemovedW", "heatBalanceErrorPercent",
    ]

    out = {}
    first = group.iloc[0]
    for col in identity_cols:
        out[col] = first[col]

    for col in metric_cols:
        if col not in group.columns:
            continue
        out[f"{col}_mean"] = group[col].mean()
        out[f"{col}_std"] = group[col].std(ddof=1) if len(group) > 1 else 0.0
        out[f"{col}_min"] = group[col].min()
        out[f"{col}_max"] = group[col].max()
        # If 8000 not present, use latest discovered sample.
        if (group["timeSample"] == 8000).any():
            out[f"{col}_final8000"] = group.loc[group["timeSample"] == 8000, col].iloc[0]
        else:
            latest_idx = group["timeSample"].idxmax()
            out[f"{col}_finalLatest"] = group.loc[latest_idx, col]

    out["nLateSamples"] = len(group)
    out["lateTimeMin"] = group["timeSample"].min()
    out["lateTimeMax"] = group["timeSample"].max()

    return pd.Series(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-matrix", default="results/tables/v02_case_matrix.csv")
    parser.add_argument("--case-root", default=".", help="Base folder for relative caseDir paths")
    parser.add_argument("--start-time", type=float, default=4000.0)
    parser.add_argument("--end-time", type=float, default=8000.0)
    parser.add_argument("--out-raw", default="results/tables/v02_global_late_times_raw.csv")
    parser.add_argument("--out-summary", default="results/tables/v02_global_late_average.csv")
    args = parser.parse_args()

    case_matrix_path = Path(args.case_matrix)
    if not case_matrix_path.exists():
        raise FileNotFoundError(f"Missing case matrix: {case_matrix_path}")

    base_dir = Path(args.case_root).resolve()
    case_matrix = pd.read_csv(case_matrix_path)

    rows = []
    for _, case_row in case_matrix.iterrows():
        case_dir = resolve_case_dir(case_row, base_dir)
        metrics_files = discover_metrics_files(case_dir, args.start_time, args.end_time)

        if not metrics_files:
            print(
                f"WARNING: no dcMetricsPlus metrics found for {case_row['caseID']} in {case_dir}/postProcessing/dcMetricsPlus "
                f"between {args.start_time:g} and {args.end_time:g}",
                file=sys.stderr,
            )
            continue

        for folder_time, metrics_path in metrics_files:
            row = read_one_metrics_file(case_row, case_dir, folder_time, metrics_path)
            if row is not None:
                rows.append(row)

    if not rows:
        raise RuntimeError("No global metrics files found. Run dcMetricsPlus in each case first.")

    raw = pd.DataFrame(rows)
    raw = add_derived_columns(raw)

    summary = (
        raw.groupby("caseID", sort=False)
        .apply(summarize_case)
        .reset_index(drop=True)
    )

    Path(args.out_raw).parent.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.out_raw, index=False)
    summary.to_csv(args.out_summary, index=False)

    print(f"Wrote {args.out_raw}")
    print(f"Wrote {args.out_summary}")


if __name__ == "__main__":
    main()
