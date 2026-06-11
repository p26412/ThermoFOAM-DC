#!/usr/bin/env python3
"""Create the ten ThermoFOAM-DC v0.2 parameter-study cases from a base OpenFOAM case.

Example from repository root:
    python3 scripts/create_parameter_cases_v02_10cases.py gridStudy_RNG/grid_10 cases/parameterstudy

The script copies the base case, removes generated result folders during copy, and edits:
- 0/U supplyTiles velocity
- 0/T supplyTiles temperature
- constant/fvModels rack heat powers
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path
from typing import Dict, Iterable, Set

RACKS = ["rack_L1", "rack_L2", "rack_L3", "rack_R1", "rack_R2", "rack_R3"]

CASE_DEFS = [
    ("C00_baseline", "(0 0 0.75)", 291.0, "base"),
    ("C01_lowSupplyVelocity", "(0 0 0.50)", 291.0, "base"),
    ("C02_highSupplyVelocity", "(0 0 1.00)", 291.0, "base"),
    ("C03_warmerSupplyAir", "(0 0 0.75)", 295.0, "base"),
    ("C04_highRackLoad", "(0 0 0.75)", 291.0, "high"),
    ("C05_overloadedRack_L2", "(0 0 0.75)", 291.0, "hotspot"),
    ("C06_worstCase_lowFlow_highLoad", "(0 0 0.50)", 291.0, "high"),
    ("C07_mitigation_highFlow_highLoad", "(0 0 1.00)", 291.0, "high"),
    ("C08_overloadedRack_L2_lowFlow", "(0 0 0.50)", 291.0, "hotspot"),
    ("C09_overloadedRack_L2_highFlow", "(0 0 1.00)", 291.0, "hotspot"),
]


def is_time_dir(name: str) -> bool:
    if name == "0":
        return False
    try:
        float(name)
        return True
    except ValueError:
        return False


def ignore_generated(_dir: str, names: Iterable[str]) -> Set[str]:
    ignored: Set[str] = set()
    for name in names:
        if is_time_dir(name):
            ignored.add(name)
        elif name.startswith("processor"):
            ignored.add(name)
        elif name in {"postProcessing", "VTK", "dynamicCode", "platforms", "__pycache__"}:
            ignored.add(name)
        elif name.startswith("log.") or name.endswith(".log") or name.endswith(".foam"):
            ignored.add(name)
    return ignored


def replace_supply_velocity(u_file: Path, vec: str) -> None:
    text = u_file.read_text()
    pattern = r"(supplyTiles\s*\{.*?value\s+uniform\s+)\([^;]+\)(\s*;)"
    new, n = re.subn(pattern, rf"\g<1>{vec}\g<2>", text, flags=re.S)
    if n != 1:
        raise RuntimeError(f"Could not replace supply velocity in {u_file}; matches={n}")
    u_file.write_text(new)


def replace_supply_temperature(t_file: Path, value: float) -> None:
    text = t_file.read_text()
    pattern = r"(supplyTiles\s*\{.*?value\s+uniform\s+)([0-9.eE+-]+)(\s*;)"
    new, n = re.subn(pattern, rf"\g<1>{value:g}\g<3>", text, flags=re.S)
    if n != 1:
        raise RuntimeError(f"Could not replace supply temperature in {t_file}; matches={n}")
    t_file.write_text(new)


def replace_rack_powers(fv_file: Path, powers: Dict[str, float]) -> None:
    text = fv_file.read_text()
    for rack, q in powers.items():
        pattern = rf"({rack}_heat\s*\{{.*?Q\s+)([0-9.eE+-]+)(\s*;)"
        text, n = re.subn(pattern, rf"\g<1>{q:g}\g<3>", text, flags=re.S)
        if n != 1:
            raise RuntimeError(f"Could not replace Q for {rack} in {fv_file}; matches={n}")
    fv_file.write_text(text)


def power_map(kind: str) -> Dict[str, float]:
    if kind == "base":
        return {r: 3000.0 for r in RACKS}
    if kind == "high":
        return {r: 5000.0 for r in RACKS}
    if kind == "hotspot":
        powers = {r: 3000.0 for r in RACKS}
        powers["rack_L2"] = 8000.0
        return powers
    raise ValueError(f"Unknown power-map kind: {kind}")


def validate_base_case(base: Path) -> None:
    required = [base / "0" / "U", base / "0" / "T", base / "constant" / "fvModels", base / "system" / "controlDict"]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise SystemExit("Base case is missing required files:\n" + "\n".join(missing))


def make_case(base: Path, outdir: Path, name: str, vel: str, temp: float, powers: Dict[str, float], overwrite: bool) -> None:
    dest = outdir / name
    if dest.exists():
        if not overwrite:
            raise SystemExit(f"Case already exists: {dest}. Use --overwrite to replace it.")
        shutil.rmtree(dest)
    shutil.copytree(base, dest, ignore=ignore_generated)
    replace_supply_velocity(dest / "0" / "U", vel)
    replace_supply_temperature(dest / "0" / "T", temp)
    replace_rack_powers(dest / "constant" / "fvModels", powers)
    print(f"Created {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create ten v0.2 ThermoFOAM-DC parameter-study cases.")
    parser.add_argument("base_case", type=Path, help="Base OpenFOAM case, preferably the grid_10 RNG case")
    parser.add_argument("outdir", type=Path, help="Output folder, for example cases/parameterstudy")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing C* case folders")
    args = parser.parse_args()

    base = args.base_case.resolve()
    outdir = args.outdir.resolve()
    validate_base_case(base)
    outdir.mkdir(parents=True, exist_ok=True)

    for name, vel, temp, kind in CASE_DEFS:
        make_case(base, outdir, name, vel, temp, power_map(kind), args.overwrite)

    print("Done. Created ten v0.2 cases in:", outdir)


if __name__ == "__main__":
    main()
