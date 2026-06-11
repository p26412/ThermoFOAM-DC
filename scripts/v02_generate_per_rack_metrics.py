#!/usr/bin/env python3
"""
Generate per-rack dcMetricsPlus outputs by temporarily replacing rackInletBoxMin/Max
with one rack inlet box at a time.

Run from parameter-study root, e.g.
    python3 scripts/v02_generate_per_rack_metrics.py

Output per case:
    postProcessing/dcMetricsPlus_perRack/L1/<time>/metrics.csv
    ...

This script preserves the original global dcMetricsPlus output by backing it up
and restoring it after each case. It also restores the original dictionary even
if a rack run fails. Because apparently one must babysit every dictionary like
it has trust issues.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

RACK_BOXES = {
    "L1": ("(1.0 2.0 0.0)", "(1.8 2.2 2.2)"),
    "L2": ("(3.1 2.0 0.0)", "(3.9 2.2 2.2)"),
    "L3": ("(5.2 2.0 0.0)", "(6.0 2.2 2.2)"),
    "R1": ("(1.0 2.8 0.0)", "(1.8 3.0 2.2)"),
    "R2": ("(3.1 2.8 0.0)", "(3.9 3.0 2.2)"),
    "R3": ("(5.2 2.8 0.0)", "(6.0 3.0 2.2)"),
}


def resolve_case_dir(case_row, base_dir: Path) -> Path:
    candidates = []
    for key in ["caseDir", "caseID", "caseName"]:
        value = str(case_row.get(key, "")).strip()
        if value and value.lower() != "nan":
            p = Path(value)
            candidates.append(p if p.is_absolute() else base_dir / p)

    for p in candidates:
        if p.exists() and p.is_dir():
            return p

    case_id = str(case_row.get("caseID", "")).strip()
    if case_id:
        matches = sorted(base_dir.glob(f"{case_id}*"))
        matches = [m for m in matches if m.is_dir()]
        if len(matches) == 1:
            return matches[0]

    raise FileNotFoundError(f"Cannot resolve case directory for {case_row.get('caseID')}")


def find_metrics_dict(case_dir: Path) -> Path:
    system_dir = case_dir / "system"
    preferred = [
        system_dir / "dcMetricsPlusDict",
        system_dir / "dcMetricsDict",
        system_dir / "dcMetricsPlus.dict",
    ]

    for p in preferred:
        if p.exists():
            text = p.read_text(errors="ignore")
            if "rackInletBoxMin" in text and "rackInletBoxMax" in text:
                return p

    # Last resort: search system directory for a dictionary containing those entries.
    for p in system_dir.glob("*"):
        if not p.is_file():
            continue
        try:
            text = p.read_text(errors="ignore")
        except Exception:
            continue
        if "rackInletBoxMin" in text and "rackInletBoxMax" in text:
            return p

    raise FileNotFoundError(
        f"Could not find dcMetrics dictionary with rackInletBoxMin/Max in {system_dir}"
    )


def replace_openfoam_list(text: str, keyword: str, new_items: list[str]) -> str:
    """Replace keyword ( ... ); block with a new OpenFOAM list."""
    pattern = re.compile(rf"({re.escape(keyword)}\s*)\([^;]*\)\s*;", re.S)
    replacement = keyword + "\n(\n" + "\n".join(f"    {item}" for item in new_items) + "\n);"
    new_text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"Could not replace {keyword} block")
    return new_text


def patch_dict_for_rack(original_text: str, rack: str) -> str:
    box_min, box_max = RACK_BOXES[rack]
    text = replace_openfoam_list(original_text, "rackInletBoxMin", [box_min])
    text = replace_openfoam_list(text, "rackInletBoxMax", [box_max])
    return text


def copytree_replace(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def run_command(cmd, cwd: Path, log_path: Path):
    with log_path.open("w") as log:
        proc = subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed in {cwd}: {' '.join(cmd)}. See {log_path}")


def generate_case(case_dir: Path, only_racks: list[str], keep_existing: bool):
    dict_path = find_metrics_dict(case_dir)
    original_text = dict_path.read_text()

    post_dir = case_dir / "postProcessing"
    global_dir = post_dir / "dcMetricsPlus"
    global_backup = post_dir / "dcMetricsPlus_globalBackupBeforePerRack"
    per_rack_root = post_dir / "dcMetricsPlus_perRack"
    per_rack_root.mkdir(parents=True, exist_ok=True)

    had_global = global_dir.exists()
    if had_global and not global_backup.exists():
        copytree_replace(global_dir, global_backup)

    try:
        for rack in only_racks:
            out_dir = per_rack_root / rack
            if keep_existing and out_dir.exists() and any(out_dir.glob("*/metrics.csv")):
                print(f"  {rack}: existing per-rack metrics found; skipping")
                continue

            print(f"  {rack}: running dcMetricsPlus")
            dict_path.write_text(patch_dict_for_rack(original_text, rack))

            if global_dir.exists():
                shutil.rmtree(global_dir)

            log_path = case_dir / f"log.dcMetricsPlus_perRack_{rack}"
            run_command(["dcMetricsPlus"], case_dir, log_path)

            if not global_dir.exists():
                raise RuntimeError(f"dcMetricsPlus did not create {global_dir}")

            copytree_replace(global_dir, out_dir)

    finally:
        # Restore original dictionary.
        dict_path.write_text(original_text)

        # Restore original global dcMetricsPlus output if it existed.
        if global_backup.exists():
            if global_dir.exists():
                shutil.rmtree(global_dir)
            shutil.copytree(global_backup, global_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-matrix", default="results/tables/v02_case_matrix.csv")
    parser.add_argument("--case-root", default=".")
    parser.add_argument("--cases", nargs="*", default=None, help="Optional case IDs to run, e.g. C05 C08 C09")
    parser.add_argument("--racks", nargs="*", default=list(RACK_BOXES.keys()), help="Racks to run")
    parser.add_argument("--keep-existing", action="store_true", help="Skip rack if output already exists")
    args = parser.parse_args()

    case_matrix_path = Path(args.case_matrix)
    if not case_matrix_path.exists():
        raise FileNotFoundError(f"Missing case matrix: {case_matrix_path}")

    case_matrix = pd.read_csv(case_matrix_path)
    base_dir = Path(args.case_root).resolve()

    selected_cases = set(args.cases) if args.cases else None
    selected_racks = args.racks

    for rack in selected_racks:
        if rack not in RACK_BOXES:
            raise ValueError(f"Unknown rack {rack}. Valid racks: {sorted(RACK_BOXES)}")

    for _, row in case_matrix.iterrows():
        case_id = str(row["caseID"])
        if selected_cases and case_id not in selected_cases:
            continue
        case_dir = resolve_case_dir(row, base_dir)
        print(f"Case {case_id}: {case_dir}")
        generate_case(case_dir, selected_racks, args.keep_existing)

    print("Done generating per-rack metrics.")


if __name__ == "__main__":
    main()
