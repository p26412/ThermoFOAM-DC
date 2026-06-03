#!/usr/bin/env python3
"""Create v0.2 parameter cases from the RNG k-epsilon baseline case.

Example:
  python3 scripts/create_parameter_cases.py cases/01_baseline_RNGkEpsilon parameterStudy --include-optional
"""
from __future__ import annotations
import argparse
import re
import shutil
from pathlib import Path

RACKS = ["rack_L1", "rack_L2", "rack_L3", "rack_R1", "rack_R2", "rack_R3"]


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


def replace_rack_powers(fv_file: Path, powers: dict[str, float]) -> None:
    text = fv_file.read_text()
    for rack, q in powers.items():
        pattern = rf"({rack}_heat\s*\{{.*?Q\s+)([0-9.eE+-]+)(\s*;)"
        text, n = re.subn(pattern, rf"\g<1>{q:g}\g<3>", text, flags=re.S)
        if n != 1:
            raise RuntimeError(f"Could not replace Q for {rack} in {fv_file}; matches={n}")
    fv_file.write_text(text)


def make_case(base: Path, outdir: Path, name: str, vel: str, temp: float, powers: dict[str, float]) -> None:
    dest = outdir / name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(base, dest)
    replace_supply_velocity(dest / "0" / "U", vel)
    replace_supply_temperature(dest / "0" / "T", temp)
    replace_rack_powers(dest / "constant" / "fvModels", powers)
    print(f"Created {dest}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_case", type=Path)
    parser.add_argument("outdir", type=Path)
    parser.add_argument("--include-optional", action="store_true", help="Also create C06 and C07 combined stress/mitigation cases")
    args = parser.parse_args()

    base = args.base_case.resolve()
    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    base_powers = {r: 3000 for r in RACKS}
    high_powers = {r: 5000 for r in RACKS}
    hotspot = {r: 3000 for r in RACKS}
    hotspot["rack_L2"] = 8000

    make_case(base, outdir, "C00_baseline", "(0 0 0.75)", 291, base_powers)
    make_case(base, outdir, "C01_lowSupplyVelocity", "(0 0 0.50)", 291, base_powers)
    make_case(base, outdir, "C02_highSupplyVelocity", "(0 0 1.00)", 291, base_powers)
    make_case(base, outdir, "C03_warmerSupplyAir", "(0 0 0.75)", 295, base_powers)
    make_case(base, outdir, "C04_highRackLoad", "(0 0 0.75)", 291, high_powers)
    make_case(base, outdir, "C05_overloadedRack_L2", "(0 0 0.75)", 291, hotspot)

    if args.include_optional:
        make_case(base, outdir, "C06_worstCase_lowFlow_highLoad", "(0 0 0.50)", 291, high_powers)
        make_case(base, outdir, "C07_mitigation_highFlow_highLoad", "(0 0 1.00)", 291, high_powers)


if __name__ == "__main__":
    main()
