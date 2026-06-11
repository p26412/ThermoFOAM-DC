#!/usr/bin/env python3
"""Generate v0.2 plots from global and optional per-rack late-average tables."""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

GLOBAL_CSV = Path("results/tables/v02_global_late_average.csv")
PER_RACK_CSV = Path("results/tables/v02_per_rack_late_average.csv")
OUTDIR = Path("results/plots/v02")

CASE_ORDER = ["C00", "C01", "C02", "C03", "C04", "C06", "C07", "C05", "C08", "C09"]
HIGH_LOAD_CASES = ["C06", "C04", "C07"]
OVERLOADED_CASES = ["C08", "C05", "C09"]
RACK_ORDER = ["L1", "L2", "L3", "R1", "R2", "R3"]


def ordered(df, case_order=CASE_ORDER):
    df = df.copy()
    df["caseID"] = pd.Categorical(df["caseID"], categories=case_order, ordered=True)
    return df.sort_values("caseID")


def require_columns(df, cols, context):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"Missing columns for {context}: {missing}")


def plot_bar(df, metric, std_metric, ylabel, filename):
    require_columns(df, ["caseID", metric, std_metric], filename)
    df = ordered(df)
    x = range(len(df))

    plt.figure(figsize=(10, 5))
    plt.bar(x, df[metric])
    plt.errorbar(x, df[metric], yerr=df[std_metric], fmt="none", capsize=4)
    plt.xticks(x, df["caseID"].astype(str), rotation=45)
    plt.ylabel(ylabel)
    plt.xlabel("Case")
    plt.tight_layout()
    plt.savefig(OUTDIR / filename, dpi=300)
    plt.close()


def plot_tradeoff(df):
    require_columns(df, ["caseID", "pressurePowerProxy_mean", "rackInletHotspotFraction_mean"], "tradeoff")
    df = ordered(df)

    plt.figure(figsize=(7, 5))
    plt.scatter(df["pressurePowerProxy_mean"], df["rackInletHotspotFraction_mean"])
    for _, row in df.iterrows():
        plt.annotate(row["caseID"], (row["pressurePowerProxy_mean"], row["rackInletHotspotFraction_mean"]), xytext=(5, 5), textcoords="offset points")
    plt.xlabel("Pressure-power proxy [W]")
    plt.ylabel("Rack inlet risk fraction, T > 305 K")
    plt.tight_layout()
    plt.savefig(OUTDIR / "tradeoff_rackRisk_vs_pressurePowerProxy.png", dpi=300)
    plt.close()


def plot_series(df, cases, y_col, yerr_col, ylabel, filename):
    require_columns(df, ["caseID", "Usupply", y_col, yerr_col], filename)
    sub = df[df["caseID"].isin(cases)].copy().sort_values("Usupply")
    if sub.empty:
        print(f"WARNING: no data for {filename}", file=sys.stderr)
        return

    plt.figure(figsize=(7, 5))
    plt.errorbar(sub["Usupply"], sub[y_col], yerr=sub[yerr_col], marker="o", capsize=4)
    for _, row in sub.iterrows():
        plt.annotate(row["caseID"], (row["Usupply"], row[y_col]), xytext=(5, 5), textcoords="offset points")
    plt.xlabel("Supply velocity [m/s]")
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(OUTDIR / filename, dpi=300)
    plt.close()


def plot_overloaded_l2(per_rack, global_df):
    needed = ["caseID", "rackID", "T95RackInlet_mean", "T95RackInlet_std", "rackInletHotspotFraction_mean", "rackInletHotspotFraction_std"]
    require_columns(per_rack, needed, "overloaded L2 plots")
    require_columns(global_df, ["caseID", "Usupply", "pressurePowerProxy_mean", "deltaP_supply_minus_return_mean"], "overloaded L2 plots")

    l2 = per_rack[(per_rack["rackID"] == "L2") & (per_rack["caseID"].isin(OVERLOADED_CASES))].copy()
    if l2.empty:
        print("WARNING: no L2 per-rack data for overloaded cases; skipping overloaded plots", file=sys.stderr)
        return

    g = global_df[global_df["caseID"].isin(OVERLOADED_CASES)].copy()
    l2 = l2.merge(g[["caseID", "Usupply", "pressurePowerProxy_mean", "deltaP_supply_minus_return_mean"]], on="caseID", how="left")
    l2 = l2.sort_values("Usupply")

    plt.figure(figsize=(7, 5))
    plt.errorbar(l2["Usupply"], l2["T95RackInlet_mean"], yerr=l2["T95RackInlet_std"], marker="o", capsize=4)
    for _, row in l2.iterrows():
        plt.annotate(row["caseID"], (row["Usupply"], row["T95RackInlet_mean"]), xytext=(5, 5), textcoords="offset points")
    plt.xlabel("Supply velocity [m/s]")
    plt.ylabel("L2 rack inlet T95 [K]")
    plt.tight_layout()
    plt.savefig(OUTDIR / "overloaded_L2_T95_vs_supplyVelocity.png", dpi=300)
    plt.close()

    plt.figure(figsize=(7, 5))
    plt.errorbar(l2["Usupply"], l2["rackInletHotspotFraction_mean"], yerr=l2["rackInletHotspotFraction_std"], marker="o", capsize=4)
    for _, row in l2.iterrows():
        plt.annotate(row["caseID"], (row["Usupply"], row["rackInletHotspotFraction_mean"]), xytext=(5, 5), textcoords="offset points")
    plt.xlabel("Supply velocity [m/s]")
    plt.ylabel("L2 rack inlet risk fraction, T > 305 K")
    plt.tight_layout()
    plt.savefig(OUTDIR / "overloaded_L2_risk_vs_supplyVelocity.png", dpi=300)
    plt.close()

    plt.figure(figsize=(7, 5))
    plt.scatter(l2["pressurePowerProxy_mean"], l2["rackInletHotspotFraction_mean"])
    for _, row in l2.iterrows():
        plt.annotate(row["caseID"], (row["pressurePowerProxy_mean"], row["rackInletHotspotFraction_mean"]), xytext=(5, 5), textcoords="offset points")
    plt.xlabel("Pressure-power proxy [W]")
    plt.ylabel("L2 rack inlet risk fraction, T > 305 K")
    plt.tight_layout()
    plt.savefig(OUTDIR / "overloaded_L2_risk_vs_pressurePowerProxy.png", dpi=300)
    plt.close()


def plot_per_rack_heatmap(per_rack, value_col, filename, title):
    require_columns(per_rack, ["caseID", "rackID", value_col], filename)
    data = per_rack[per_rack["caseID"].isin(OVERLOADED_CASES)].copy()
    if data.empty:
        print(f"WARNING: no overloaded per-rack data for {filename}", file=sys.stderr)
        return

    pivot = data.pivot(index="caseID", columns="rackID", values=value_col)
    pivot = pivot.reindex(index=OVERLOADED_CASES, columns=RACK_ORDER)

    plt.figure(figsize=(8, 4))
    plt.imshow(pivot.values, aspect="auto")
    plt.xticks(range(len(RACK_ORDER)), RACK_ORDER)
    plt.yticks(range(len(pivot.index)), pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            value = pivot.values[i, j]
            if pd.notna(value):
                plt.text(j, i, f"{value:.2f}", ha="center", va="center")
    plt.colorbar(label=title)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(OUTDIR / filename, dpi=300)
    plt.close()


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)

    if not GLOBAL_CSV.exists():
        raise FileNotFoundError(f"Missing {GLOBAL_CSV}. Run v02_collect_global_metrics.py first.")

    df = pd.read_csv(GLOBAL_CSV)

    plot_bar(df, "T95RackInlet_mean", "T95RackInlet_std", "Rack inlet T95 [K]", "T95RackInlet_by_case.png")
    plot_bar(df, "rackInletHotspotFraction_mean", "rackInletHotspotFraction_std", "Rack inlet risk fraction, T > 305 K", "rackRiskFraction305_by_case.png")
    plot_bar(df, "roomHotspotVolumeFraction_mean", "roomHotspotVolumeFraction_std", "Room hotspot fraction, T > 315 K", "roomHotspotFraction315_by_case.png")
    plot_bar(df, "deltaP_supply_minus_return_mean", "deltaP_supply_minus_return_std", "Supply-return pressure difference [Pa]", "deltaP_by_case.png")
    plot_bar(df, "pressurePowerProxy_mean", "pressurePowerProxy_std", "Pressure-power proxy [W]", "pressurePowerProxy_by_case.png")
    plot_tradeoff(df)

    plot_series(df, HIGH_LOAD_CASES, "T95RackInlet_mean", "T95RackInlet_std", "Rack inlet T95 [K]", "highLoad_T95_vs_supplyVelocity.png")
    plot_series(df, HIGH_LOAD_CASES, "rackInletHotspotFraction_mean", "rackInletHotspotFraction_std", "Rack inlet risk fraction, T > 305 K", "highLoad_risk_vs_supplyVelocity.png")
    plot_series(df, HIGH_LOAD_CASES, "deltaP_supply_minus_return_mean", "deltaP_supply_minus_return_std", "Supply-return pressure difference [Pa]", "highLoad_deltaP_vs_supplyVelocity.png")

    if PER_RACK_CSV.exists():
        per_rack = pd.read_csv(PER_RACK_CSV)
        plot_overloaded_l2(per_rack, df)
        plot_per_rack_heatmap(per_rack, "T95RackInlet_mean", "perRack_T95RackInlet_overloaded_cases.png", "Per-rack inlet T95 [K]")
        plot_per_rack_heatmap(per_rack, "rackInletHotspotFraction_mean", "perRack_riskFraction305_overloaded_cases.png", "Per-rack risk fraction, T > 305 K")
    else:
        print(f"NOTE: {PER_RACK_CSV} not found; skipping per-rack plots.")

    print(f"Wrote plots to {OUTDIR}")


if __name__ == "__main__":
    main()
