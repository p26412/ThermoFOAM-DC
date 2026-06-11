#!/usr/bin/env python3
"""
ThermoFOAM-DC v0.2 table/plot generator.

This script intentionally avoids numpy, pandas, and matplotlib so it will run even
when the Python plotting stack is broken by a NumPy 1.x/2.x mismatch. Because
apparently one parametric CFD study was not enough pain for one lifetime.

Default use from repository root:
    python3 scripts/v02_generate_tables_and_plots.py

Optional use with local OpenFOAM case folders:
    python3 scripts/v02_generate_tables_and_plots.py --cases-root cases/parameterstudy

Expected local OpenFOAM metric location:
    <caseFolder>/postProcessing/dcMetricsPlus/<time>/metrics.csv

If no local OpenFOAM outputs are found, the script uses the provided input summary
CSV files under inputs/.
"""
from __future__ import annotations

import argparse
import csv
import glob
import math
import statistics
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

RACK_ORDER = ["L1", "L2", "L3", "R1", "R2", "R3"]

GLOBAL_METRICS = [
    "TavgRackInlet",
    "T95RackInlet",
    "TmaxRackInlet",
    "TavgRoom",
    "T95Room",
    "TmaxRoom",
    "roomHotspotVolumeFraction",
    "rackInletHotspotFraction",
    "returnOutletTmassFlowAvg",
    "returnOutletOutflowFlux",
    "deltaP_supply_minus_return",
    "pressurePowerProxy",
    "flowBalanceErrorPercent",
    "estimatedHeatRemovedW",
    "heatBalanceErrorPercent",
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


def write_csv(path: Path, rows: Sequence[Dict], fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        if fieldnames:
            with path.open("w", newline="") as f:
                csv.DictWriter(f, fieldnames=fieldnames).writeheader()
        return
    if fieldnames is None:
        seen = []
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.append(key)
        fieldnames = seen
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def svg_escape(text) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def nice_min_max(values: Sequence[float], pad_frac: float = 0.08) -> Tuple[float, float]:
    vals = [v for v in values if not math.isnan(v)]
    if not vals:
        return 0.0, 1.0
    mn, mx = min(vals), max(vals)
    if math.isclose(mn, mx):
        pad = abs(mx) * 0.1 if mx else 1.0
        return mn - pad, mx + pad
    pad = (mx - mn) * pad_frac
    return mn - pad, mx + pad


def value_to_y(value: float, ymin: float, ymax: float, top: float, height: float) -> float:
    if math.isnan(value):
        return top + height
    return top + height - (value - ymin) / (ymax - ymin) * height


def value_to_x(value: float, xmin: float, xmax: float, left: float, width: float) -> float:
    if math.isnan(value):
        return left
    return left + (value - xmin) / (xmax - xmin) * width


def case_label(row: Dict[str, str]) -> str:
    return row.get("caseID") or row.get("caseName") or "case"


def bar_chart_svg(
    rows: Sequence[Dict[str, str]],
    value_col: str,
    std_col: str | None,
    title: str,
    ylabel: str,
    outpath: Path,
    y0: float | None = None,
) -> None:
    width, height = 1180, 720
    left, right, top, bottom = 92, 40, 70, 135
    plot_w = width - left - right
    plot_h = height - top - bottom
    values = [to_float(r.get(value_col)) for r in rows]
    stds = [to_float(r.get(std_col), 0.0) if std_col else 0.0 for r in rows]
    all_y = []
    for v, s in zip(values, stds):
        if not math.isnan(v):
            all_y.extend([v - s, v + s])
    ymin, ymax = nice_min_max(all_y)
    if y0 is not None:
        ymin = y0
    if math.isclose(ymin, ymax):
        ymax = ymin + 1

    n = len(rows)
    gap = 14
    bar_w = max(16, (plot_w - gap * (n + 1)) / max(n, 1))
    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    parts.append('<rect width="100%" height="100%" fill="white"/>')
    parts.append(f'<text x="{width/2}" y="34" text-anchor="middle" font-family="Arial" font-size="24" font-weight="bold">{svg_escape(title)}</text>')
    parts.append(f'<text x="24" y="{top + plot_h/2}" transform="rotate(-90 24 {top + plot_h/2})" text-anchor="middle" font-family="Arial" font-size="17">{svg_escape(ylabel)}</text>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="black"/>')
    parts.append(f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="black"/>')

    # Horizontal grid and ticks
    for i in range(6):
        val = ymin + i * (ymax - ymin) / 5
        y = value_to_y(val, ymin, ymax, top, plot_h)
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left+plot_w}" y2="{y:.2f}" stroke="#dddddd"/>')
        parts.append(f'<text x="{left-8}" y="{y+5:.2f}" text-anchor="end" font-family="Arial" font-size="13">{fmt(val,3)}</text>')

    for i, row in enumerate(rows):
        x = left + gap + i * (bar_w + gap)
        v = values[i]
        s = stds[i]
        y = value_to_y(v, ymin, ymax, top, plot_h)
        y_base = value_to_y(ymin, ymin, ymax, top, plot_h)
        h = y_base - y
        parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{h:.2f}" fill="#9ecae1" stroke="#333333"/>')
        if std_col and not math.isnan(s):
            y_hi = value_to_y(v + s, ymin, ymax, top, plot_h)
            y_lo = value_to_y(v - s, ymin, ymax, top, plot_h)
            cx = x + bar_w / 2
            parts.append(f'<line x1="{cx:.2f}" y1="{y_hi:.2f}" x2="{cx:.2f}" y2="{y_lo:.2f}" stroke="#222222" stroke-width="2"/>')
            parts.append(f'<line x1="{cx-7:.2f}" y1="{y_hi:.2f}" x2="{cx+7:.2f}" y2="{y_hi:.2f}" stroke="#222222" stroke-width="2"/>')
            parts.append(f'<line x1="{cx-7:.2f}" y1="{y_lo:.2f}" x2="{cx+7:.2f}" y2="{y_lo:.2f}" stroke="#222222" stroke-width="2"/>')
        parts.append(f'<text x="{x + bar_w/2:.2f}" y="{height-80}" text-anchor="middle" font-family="Arial" font-size="14">{svg_escape(case_label(row))}</text>')
        parts.append(f'<text x="{x + bar_w/2:.2f}" y="{y-6:.2f}" text-anchor="middle" font-family="Arial" font-size="11">{fmt(v,3)}</text>')

    parts.append('</svg>')
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text("\n".join(parts))


def scatter_svg(
    rows: Sequence[Dict[str, str]],
    x_col: str,
    y_col: str,
    title: str,
    xlabel: str,
    ylabel: str,
    outpath: Path,
) -> None:
    width, height = 920, 700
    left, right, top, bottom = 95, 40, 75, 90
    plot_w = width - left - right
    plot_h = height - top - bottom
    xs = [to_float(r.get(x_col)) for r in rows]
    ys = [to_float(r.get(y_col)) for r in rows]
    xmin, xmax = nice_min_max(xs, 0.1)
    ymin, ymax = nice_min_max(ys, 0.1)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    parts.append('<rect width="100%" height="100%" fill="white"/>')
    parts.append(f'<text x="{width/2}" y="34" text-anchor="middle" font-family="Arial" font-size="23" font-weight="bold">{svg_escape(title)}</text>')
    parts.append(f'<text x="{left + plot_w/2}" y="{height-35}" text-anchor="middle" font-family="Arial" font-size="17">{svg_escape(xlabel)}</text>')
    parts.append(f'<text x="25" y="{top + plot_h/2}" transform="rotate(-90 25 {top + plot_h/2})" text-anchor="middle" font-family="Arial" font-size="17">{svg_escape(ylabel)}</text>')
    parts.append(f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="black"/>')
    for i in range(6):
        xv = xmin + i*(xmax-xmin)/5
        x = value_to_x(xv, xmin, xmax, left, plot_w)
        parts.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top+plot_h}" stroke="#eeeeee"/>')
        parts.append(f'<text x="{x:.2f}" y="{top+plot_h+20}" text-anchor="middle" font-family="Arial" font-size="12">{fmt(xv,3)}</text>')
        yv = ymin + i*(ymax-ymin)/5
        y = value_to_y(yv, ymin, ymax, top, plot_h)
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left+plot_w}" y2="{y:.2f}" stroke="#eeeeee"/>')
        parts.append(f'<text x="{left-8}" y="{y+5:.2f}" text-anchor="end" font-family="Arial" font-size="12">{fmt(yv,3)}</text>')
    for r, xval, yval in zip(rows, xs, ys):
        if math.isnan(xval) or math.isnan(yval):
            continue
        x = value_to_x(xval, xmin, xmax, left, plot_w)
        y = value_to_y(yval, ymin, ymax, top, plot_h)
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="7" fill="#fb6a4a" stroke="#222"/>')
        parts.append(f'<text x="{x+10:.2f}" y="{y-8:.2f}" font-family="Arial" font-size="12">{svg_escape(case_label(r))}</text>')
    parts.append('</svg>')
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text("\n".join(parts))


def color_ramp(value: float, vmin: float, vmax: float) -> str:
    if math.isnan(value):
        return "#f0f0f0"
    t = 0.0 if math.isclose(vmin, vmax) else max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))
    # Blue-white-red-ish without external libraries.
    if t < 0.5:
        u = t / 0.5
        r = int(49 + (247 - 49) * u)
        g = int(130 + (247 - 130) * u)
        b = int(189 + (247 - 189) * u)
    else:
        u = (t - 0.5) / 0.5
        r = int(247 + (203 - 247) * u)
        g = int(247 + (24 - 247) * u)
        b = int(247 + (29 - 247) * u)
    return f"#{r:02x}{g:02x}{b:02x}"


def heatmap_svg(
    rows: Sequence[Dict[str, str]],
    value_col: str,
    title: str,
    outpath: Path,
) -> None:
    cases = []
    for r in rows:
        cid = r.get("caseID", "")
        if cid and cid not in cases:
            cases.append(cid)
    values = {(r.get("rackID"), r.get("caseID")): to_float(r.get(value_col)) for r in rows}
    vals = [v for v in values.values() if not math.isnan(v)]
    vmin, vmax = (min(vals), max(vals)) if vals else (0.0, 1.0)
    cell_w, cell_h = 84, 44
    left, top = 95, 72
    width = left + cell_w * len(cases) + 80
    height = top + cell_h * len(RACK_ORDER) + 105
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    parts.append('<rect width="100%" height="100%" fill="white"/>')
    parts.append(f'<text x="{width/2}" y="34" text-anchor="middle" font-family="Arial" font-size="22" font-weight="bold">{svg_escape(title)}</text>')
    for j, cid in enumerate(cases):
        x = left + j * cell_w + cell_w/2
        parts.append(f'<text x="{x:.1f}" y="{top-12}" text-anchor="middle" font-family="Arial" font-size="13">{svg_escape(cid)}</text>')
    for i, rack in enumerate(RACK_ORDER):
        y = top + i * cell_h + cell_h/2 + 5
        parts.append(f'<text x="{left-12}" y="{y:.1f}" text-anchor="end" font-family="Arial" font-size="14">{rack}</text>')
        for j, cid in enumerate(cases):
            v = values.get((rack, cid), float("nan"))
            x0 = left + j * cell_w
            y0 = top + i * cell_h
            parts.append(f'<rect x="{x0}" y="{y0}" width="{cell_w}" height="{cell_h}" fill="{color_ramp(v, vmin, vmax)}" stroke="white"/>')
            parts.append(f'<text x="{x0+cell_w/2:.1f}" y="{y0+cell_h/2+5:.1f}" text-anchor="middle" font-family="Arial" font-size="12">{fmt(v,3)}</text>')
    parts.append(f'<text x="{left}" y="{height-35}" font-family="Arial" font-size="13">Scale: {fmt(vmin,3)} to {fmt(vmax,3)}</text>')
    parts.append('</svg>')
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text("\n".join(parts))


def line_chart_svg(
    rows: Sequence[Dict[str, str]],
    value_col: str,
    title: str,
    ylabel: str,
    outpath: Path,
) -> None:
    by_case: Dict[str, List[Dict[str, str]]] = {}
    for r in rows:
        by_case.setdefault(r.get("caseID", "case"), []).append(r)
    for cid in by_case:
        by_case[cid].sort(key=lambda r: to_float(r.get("time") or r.get("timeSample")))
    width, height = 1100, 700
    left, right, top, bottom = 85, 180, 70, 85
    plot_w = width - left - right
    plot_h = height - top - bottom
    xs = [to_float(r.get("time") or r.get("timeSample")) for r in rows]
    ys = [to_float(r.get(value_col)) for r in rows]
    xmin, xmax = nice_min_max(xs, 0.02)
    ymin, ymax = nice_min_max(ys, 0.08)
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    parts.append('<rect width="100%" height="100%" fill="white"/>')
    parts.append(f'<text x="{width/2}" y="34" text-anchor="middle" font-family="Arial" font-size="22" font-weight="bold">{svg_escape(title)}</text>')
    parts.append(f'<text x="{left+plot_w/2}" y="{height-35}" text-anchor="middle" font-family="Arial" font-size="16">Time sample</text>')
    parts.append(f'<text x="24" y="{top + plot_h/2}" transform="rotate(-90 24 {top + plot_h/2})" text-anchor="middle" font-family="Arial" font-size="16">{svg_escape(ylabel)}</text>')
    parts.append(f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="none" stroke="black"/>')
    for idx, (cid, series) in enumerate(by_case.items()):
        color = palette[idx % len(palette)]
        pts = []
        for r in series:
            xval = to_float(r.get("time") or r.get("timeSample"))
            yval = to_float(r.get(value_col))
            if math.isnan(xval) or math.isnan(yval):
                continue
            pts.append((value_to_x(xval, xmin, xmax, left, plot_w), value_to_y(yval, ymin, ymax, top, plot_h)))
        if len(pts) >= 2:
            path = " ".join([f"{x:.1f},{y:.1f}" for x, y in pts])
            parts.append(f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="2"/>')
        for x, y in pts:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{color}"/>')
        ly = top + 18 + idx * 20
        parts.append(f'<rect x="{left+plot_w+25}" y="{ly-10}" width="12" height="12" fill="{color}"/>')
        parts.append(f'<text x="{left+plot_w+43}" y="{ly}" font-family="Arial" font-size="13">{svg_escape(cid)}</text>')
    parts.append('</svg>')
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text("\n".join(parts))


def derive_global(row: Dict[str, str]) -> Dict[str, str]:
    out = dict(row)
    us = to_float(out.get("Usupply"))
    ts = to_float(out.get("Tsupply"))
    total_vol = to_float(out.get("totalVolume"), 105.0)
    q = to_float(out.get("totalRackPowerW"))
    expected_flow = to_float(out.get("expectedSupplyFlow"))
    flux = to_float(out.get("returnOutletOutflowFlux"))
    dp = to_float(out.get("deltaP_supply_minus_return"))
    ret_t = to_float(out.get("returnOutletTmassFlowAvg"))
    if not math.isnan(ts):
        for key in ["TavgRackInlet", "T95RackInlet", "TmaxRackInlet", "TavgRoom", "T95Room", "TmaxRoom"]:
            if key in out:
                out[key + "Rise"] = fmt(to_float(out.get(key)) - ts)
    if not math.isnan(ret_t) and not math.isnan(ts):
        out["returnTempRise"] = fmt(ret_t - ts)
    if not math.isnan(expected_flow) and expected_flow != 0 and not math.isnan(flux):
        out["flowBalanceErrorPercent"] = fmt(abs(flux - expected_flow) / expected_flow * 100.0)
    if not math.isnan(dp) and not math.isnan(flux):
        out["pressurePowerProxy"] = fmt(dp * flux)
    if not math.isnan(flux) and not math.isnan(total_vol) and total_vol != 0:
        out["airChangesPerHour"] = fmt(flux * 3600.0 / total_vol)
    # Diagnostic only: assumes returnOutletOutflowFlux behaves like volumetric flow rate, rho=1.2 kg/m3, cp=1005 J/kg-K.
    if not math.isnan(flux) and not math.isnan(ret_t) and not math.isnan(ts):
        heat_removed = 1.2 * 1005.0 * flux * (ret_t - ts)
        out["estimatedHeatRemovedW"] = fmt(heat_removed)
        if not math.isnan(q) and q != 0:
            out["heatBalanceErrorPercent"] = fmt(abs(heat_removed - q) / q * 100.0)
    return out


def collect_global_timeseries(cases_root: Path, case_matrix: Sequence[Dict[str, str]], late_start: float) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for case in case_matrix:
        folder = case.get("folder") or case.get("caseDir") or case.get("caseID")
        case_dir = cases_root / folder
        if not case_dir.exists():
            # Also accept C00 instead of C00_baseline because OpenFOAM users enjoy naming chaos.
            alt = cases_root / case.get("caseID", "")
            case_dir = alt if alt.exists() else case_dir
        pattern = str(case_dir / "postProcessing" / "dcMetricsPlus" / "*" / "metrics.csv")
        for p in sorted(glob.glob(pattern)):
            data = read_csv(Path(p))
            for r in data:
                t = to_float(r.get("time"))
                if math.isnan(t):
                    # Use parent folder name as time if CSV lacks time.
                    t = to_float(Path(p).parent.name)
                    r["time"] = fmt(t)
                if t < late_start:
                    continue
                merged = dict(r)
                for k, v in case.items():
                    merged.setdefault(k, v)
                merged["caseDir"] = str(case_dir)
                rows.append(derive_global(merged))
    return rows


def summarize_global_timeseries(rows: Sequence[Dict[str, str]], case_matrix: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    by_case: Dict[str, List[Dict[str, str]]] = {}
    meta = {r.get("caseID"): r for r in case_matrix}
    for r in rows:
        by_case.setdefault(r.get("caseID", ""), []).append(r)
    summary: List[Dict[str, str]] = []
    for cid in [r.get("caseID") for r in case_matrix]:
        group = by_case.get(cid, [])
        if not group:
            continue
        group = sorted(group, key=lambda r: to_float(r.get("time")))
        out = dict(meta.get(cid, {}))
        out["nLateSamples"] = len(group)
        out["lateTimeMin"] = fmt(min(to_float(r.get("time")) for r in group))
        out["lateTimeMax"] = fmt(max(to_float(r.get("time")) for r in group))
        for m in GLOBAL_METRICS:
            vals = [to_float(r.get(m)) for r in group if not math.isnan(to_float(r.get(m)))]
            if vals:
                out[m + "_mean"] = fmt(statistics.mean(vals))
                out[m + "_std"] = fmt(statistics.stdev(vals) if len(vals) > 1 else 0.0)
                out[m + "_min"] = fmt(min(vals))
                out[m + "_max"] = fmt(max(vals))
                out[m + "_final8000"] = fmt(to_float(group[-1].get(m)))
        summary.append(out)
    return summary


def compact_global_summary(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    wanted = [
        "caseID", "caseName", "Usupply", "Tsupply", "totalRackPowerW", "expectedSupplyFlow", "nLateSamples",
        "TavgRackInlet_mean", "TavgRackInlet_std", "T95RackInlet_mean", "T95RackInlet_std", "TmaxRackInlet_mean", "TmaxRackInlet_std",
        "TavgRoom_mean", "T95Room_mean", "TmaxRoom_mean",
        "rackInletHotspotFraction_mean", "rackInletHotspotFraction_std",
        "roomHotspotVolumeFraction_mean", "roomHotspotVolumeFraction_std",
        "returnOutletTmassFlowAvg_mean", "returnOutletOutflowFlux_mean",
        "deltaP_supply_minus_return_mean", "pressurePowerProxy_mean",
        "flowBalanceErrorPercent_mean", "estimatedHeatRemovedW_mean", "heatBalanceErrorPercent_mean",
    ]
    return [{k: r.get(k, "") for k in wanted} for r in rows]


def make_flow_table(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    out = []
    for r in rows:
        out.append({
            "caseID": r.get("caseID"),
            "caseName": r.get("caseName"),
            "Usupply": r.get("Usupply"),
            "expectedSupplyFlow": r.get("expectedSupplyFlow"),
            "returnOutletOutflowFlux_mean": r.get("returnOutletOutflowFlux_mean"),
            "returnOutletOutflowFlux_std": r.get("returnOutletOutflowFlux_std"),
            "flowBalanceErrorPercent_mean": r.get("flowBalanceErrorPercent_mean"),
            "flowBalanceErrorPercent_std": r.get("flowBalanceErrorPercent_std"),
            "note": "Uses return outlet flux against expected supply flow; diagnostic, not a full mass-conservation proof.",
        })
    return out


def make_heat_table(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    out = []
    for r in rows:
        out.append({
            "caseID": r.get("caseID"),
            "caseName": r.get("caseName"),
            "totalRackPowerW": r.get("totalRackPowerW"),
            "estimatedHeatRemovedW_mean": r.get("estimatedHeatRemovedW_mean"),
            "estimatedHeatRemovedW_std": r.get("estimatedHeatRemovedW_std"),
            "heatBalanceErrorPercent_mean": r.get("heatBalanceErrorPercent_mean"),
            "heatBalanceErrorPercent_std": r.get("heatBalanceErrorPercent_std"),
            "note": "Return-outlet heat-removal diagnostic only. For publication, integrate enthalpy over all open boundaries.",
        })
    return out


def make_main_findings(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    baseline = next((r for r in rows if r.get("caseID") == "C00"), None)
    findings = []
    if not baseline:
        return findings
    b_t95 = to_float(baseline.get("T95RackInlet_mean"))
    b_risk = to_float(baseline.get("rackInletHotspotFraction_mean"))
    b_room = to_float(baseline.get("roomHotspotVolumeFraction_mean"))
    b_proxy = to_float(baseline.get("pressurePowerProxy_mean"))
    for r in rows:
        findings.append({
            "caseID": r.get("caseID"),
            "caseName": r.get("caseName"),
            "T95RackInlet_mean_K": r.get("T95RackInlet_mean"),
            "delta_T95RackInlet_vs_C00_K": fmt(to_float(r.get("T95RackInlet_mean")) - b_t95),
            "rackInletHotspotFraction_mean": r.get("rackInletHotspotFraction_mean"),
            "delta_rackRisk_vs_C00": fmt(to_float(r.get("rackInletHotspotFraction_mean")) - b_risk),
            "roomHotspotVolumeFraction_mean": r.get("roomHotspotVolumeFraction_mean"),
            "delta_roomHotspot_vs_C00": fmt(to_float(r.get("roomHotspotVolumeFraction_mean")) - b_room),
            "pressureFlowProxy_mean": r.get("pressurePowerProxy_mean"),
            "delta_pressureProxy_vs_C00": fmt(to_float(r.get("pressurePowerProxy_mean")) - b_proxy),
        })
    return findings


def per_rack_ranking(rows: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    rank = []
    for r in rows:
        rank.append({
            "caseID": r.get("caseID"),
            "caseName": r.get("caseName"),
            "rackID": r.get("rackID"),
            "rackPowerW": r.get("rackPowerW"),
            "TavgRackInlet_mean": r.get("TavgRackInlet_mean"),
            "T95RackInlet_mean": r.get("T95RackInlet_mean"),
            "TmaxRackInlet_mean": r.get("TmaxRackInlet_mean"),
            "rackInletHotspotFraction_mean": r.get("rackInletHotspotFraction_mean"),
        })
    rank.sort(key=lambda r: to_float(r.get("rackInletHotspotFraction_mean")), reverse=True)
    for i, r in enumerate(rank, 1):
        r["rank_by_rackRisk"] = i
    return rank


def write_markdown_table(path: Path, rows: Sequence[Dict[str, str]], columns: Sequence[str], title: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if title:
        lines.append(f"# {title}\n")
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "|".join(["---"] * len(columns)) + "|")
    for r in rows:
        lines.append("| " + " | ".join(svg_escape(r.get(c, "")) for c in columns) + " |")
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    default_root = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description="Generate ThermoFOAM-DC v0.2 tables and SVG plots without pandas/matplotlib.")
    p.add_argument("--project-root", type=Path, default=default_root)
    p.add_argument("--cases-root", type=Path, default=None, help="Optional OpenFOAM parameter study folder. Default: <project-root>/cases/parameterstudy")
    p.add_argument("--late-start", type=float, default=4000.0)
    args = p.parse_args()

    root = args.project_root.resolve()

    def has_case_data(path: Path) -> bool:
        """Return True if a directory looks like a parameter-study cases root."""
        if any(path.glob("*/postProcessing/dcMetricsPlus/*/metrics.csv")):
            return True
        # Accept either verbose folders like C00_baseline or compact folders like C00.
        for name in ("C00_baseline", "C00", "C01_lowSupplyVelocity", "C01"):
            if (path / name).exists():
                return True
        return False

    if args.cases_root:
        cases_root = args.cases_root.resolve()
    else:
        candidates = [
            root / "cases" / "parameterstudy",   # normal repo-root layout
            root,                                  # when this pack is placed inside cases/parameterstudy
            root.parent / "parameterstudy",        # when script is run from a sibling utility folder
        ]
        cases_root = next((c.resolve() for c in candidates if has_case_data(c)), (root / "cases" / "parameterstudy").resolve())

    out_tables = root / "results" / "tables"
    out_plots = root / "results" / "plots" / "publication"
    out_docs = root / "docs"
    out_tables.mkdir(parents=True, exist_ok=True)
    out_plots.mkdir(parents=True, exist_ok=True)

    case_matrix = read_csv(root / "metadata" / "v02_case_matrix.csv")
    if not case_matrix:
        raise SystemExit("Missing metadata/v02_case_matrix.csv")

    # Prefer local OpenFOAM data when it exists. Fallback to provided summary.
    timeseries = collect_global_timeseries(cases_root, case_matrix, args.late_start)
    if timeseries:
        write_csv(out_tables / "v02_global_timeseries.csv", timeseries)
        global_summary = summarize_global_timeseries(timeseries, case_matrix)
    else:
        global_summary = read_csv(root / "inputs" / "v02_global_summary_user.csv")
        if not global_summary:
            raise SystemExit("No local dcMetricsPlus outputs found and no inputs/v02_global_summary_user.csv found.")

    # Stable case ordering from case matrix.
    order = {r.get("caseID"): i for i, r in enumerate(case_matrix)}
    global_summary.sort(key=lambda r: order.get(r.get("caseID"), 999))

    write_csv(out_tables / "v02_global_summary.csv", global_summary)
    write_csv(out_tables / "v02_global_summary_compact.csv", compact_global_summary(global_summary))
    write_csv(out_tables / "v02_flow_balance_table.csv", make_flow_table(global_summary))
    write_csv(out_tables / "v02_heat_balance_diagnostic_table.csv", make_heat_table(global_summary))
    write_csv(out_tables / "v02_main_findings.csv", make_main_findings(global_summary))

    yplus = read_csv(root / "inputs" / "v02_yplus_table_user.csv")
    if yplus:
        write_csv(out_tables / "v02_yplus_table.csv", yplus)

    mesh_ref = read_csv(root / "inputs" / "v02_mesh_independence_reference_template.csv")
    if mesh_ref:
        write_csv(out_tables / "v02_mesh_independence_reference.csv", mesh_ref)

    # Per-rack summary from provided/user-generated CSV.
    per_rack = read_csv(root / "inputs" / "v02_per_rack_summary_user.csv")
    if per_rack:
        per_rack.sort(key=lambda r: (order.get(r.get("caseID"), 999), RACK_ORDER.index(r.get("rackID")) if r.get("rackID") in RACK_ORDER else 99))
        write_csv(out_tables / "v02_per_rack_summary.csv", per_rack)
        write_csv(out_tables / "v02_per_rack_hotspot_ranking.csv", per_rack_ranking(per_rack))

    # Plots from summary.
    bar_chart_svg(global_summary, "TavgRackInlet_mean", "TavgRackInlet_std", "Late-window mean rack-inlet average temperature", "Temperature [K]", out_plots / "Fig02_TavgRackInlet_mean_std.svg")
    bar_chart_svg(global_summary, "T95RackInlet_mean", "T95RackInlet_std", "Late-window mean rack-inlet 95th percentile temperature", "Temperature [K]", out_plots / "Fig03_T95RackInlet_mean_std.svg")
    bar_chart_svg(global_summary, "rackInletHotspotFraction_mean", "rackInletHotspotFraction_std", "Late-window rack-inlet risk fraction", "Fraction above 305 K [-]", out_plots / "Fig04_rackRiskFraction_mean_std.svg", y0=0.0)
    bar_chart_svg(global_summary, "roomHotspotVolumeFraction_mean", "roomHotspotVolumeFraction_std", "Late-window room hotspot volume fraction", "Fraction above 315 K [-]", out_plots / "Fig05_roomHotspotFraction_mean_std.svg", y0=0.0)
    bar_chart_svg(global_summary, "pressurePowerProxy_mean", "pressurePowerProxy_std", "Pressure-flow proxy", "Delta p x return flow [proxy units]", out_plots / "Fig06_pressureFlowProxy_mean_std.svg", y0=0.0)
    scatter_svg(global_summary, "pressurePowerProxy_mean", "T95RackInlet_mean", "Thermal risk versus pressure-flow proxy", "Pressure-flow proxy", "T95 rack inlet [K]", out_plots / "Fig07_pressureProxy_vs_T95RackInlet.svg")
    bar_chart_svg(global_summary, "flowBalanceErrorPercent_mean", "flowBalanceErrorPercent_std", "Flow balance diagnostic", "Error [%]", out_plots / "Fig10_flowBalanceErrorPercent_mean_std.svg", y0=0.0)
    bar_chart_svg(global_summary, "heatBalanceErrorPercent_mean", "heatBalanceErrorPercent_std", "Return-outlet heat-removal diagnostic", "Error [%]", out_plots / "Fig11_heatBalanceDiagnostic_mean_std.svg", y0=0.0)

    if per_rack:
        heatmap_svg(per_rack, "TavgRackInlet_mean", "Per-rack mean inlet temperature [K]", out_plots / "Fig08_perRack_Tavg_heatmap.svg")
        heatmap_svg(per_rack, "T95RackInlet_mean", "Per-rack 95th percentile inlet temperature [K]", out_plots / "Fig09_perRack_T95_heatmap.svg")
        heatmap_svg(per_rack, "rackInletHotspotFraction_mean", "Per-rack inlet risk fraction [-]", out_plots / "Fig12_perRack_risk_heatmap.svg")

    # Optional time history if local timeseries exists.
    if timeseries:
        line_chart_svg(timeseries, "TavgRackInlet", "Late-window time history: TavgRackInlet", "Temperature [K]", out_plots / "Fig13_timeHistory_TavgRackInlet.svg")
        line_chart_svg(timeseries, "rackInletHotspotFraction", "Late-window time history: rack inlet risk", "Fraction above 305 K [-]", out_plots / "Fig14_timeHistory_rackRiskFraction.svg")
        line_chart_svg(timeseries, "roomHotspotVolumeFraction", "Late-window time history: room hotspot fraction", "Fraction above 315 K [-]", out_plots / "Fig15_timeHistory_roomHotspotFraction.svg")

    # Markdown quick-look tables for GitHub rendering.
    write_markdown_table(
        out_docs / "v02_main_findings.md",
        make_main_findings(global_summary),
        ["caseID", "caseName", "T95RackInlet_mean_K", "delta_T95RackInlet_vs_C00_K", "rackInletHotspotFraction_mean", "roomHotspotVolumeFraction_mean", "pressureFlowProxy_mean"],
        "v0.2 main findings"
    )
    write_markdown_table(
        out_docs / "v02_flow_balance_table.md",
        make_flow_table(global_summary),
        ["caseID", "caseName", "expectedSupplyFlow", "returnOutletOutflowFlux_mean", "flowBalanceErrorPercent_mean", "note"],
        "v0.2 flow balance diagnostic"
    )
    write_markdown_table(
        out_docs / "v02_heat_balance_diagnostic_table.md",
        make_heat_table(global_summary),
        ["caseID", "caseName", "totalRackPowerW", "estimatedHeatRemovedW_mean", "heatBalanceErrorPercent_mean", "note"],
        "v0.2 heat-removal diagnostic"
    )

    print("Generated v0.2 tables in:", out_tables)
    print("Generated v0.2 SVG plots in:", out_plots)
    if timeseries:
        print("Read local OpenFOAM dcMetricsPlus rows:", len(timeseries))
        print("Cases root used:", cases_root)
    else:
        print("Note: No local OpenFOAM dcMetricsPlus time folders were found, so summary CSV inputs were used.")
        print("      Cases root searched:", cases_root)
        print("      To create time-history plots, pass the actual folder that contains C00_baseline, C01_lowSupplyVelocity, etc.")


if __name__ == "__main__":
    main()
