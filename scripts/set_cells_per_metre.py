#!/usr/bin/env python3
"""Edit cellsPerMetreX/Y/Z in system/blockMeshDict."""
from __future__ import annotations
import argparse
import re
from pathlib import Path


def replace_value(text: str, key: str, value: int) -> str:
    pattern = rf"^({re.escape(key)}\s+)\S+(\s*;)"
    repl = rf"\g<1>{value}\g<2>"
    new, n = re.subn(pattern, repl, text, flags=re.MULTILINE)
    if n != 1:
        raise RuntimeError(f"Could not replace {key}; found {n} matches")
    return new


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("case", type=Path, help="OpenFOAM case directory")
    ap.add_argument("--x", type=int, required=True)
    ap.add_argument("--y", type=int, required=True)
    ap.add_argument("--z", type=int, required=True)
    args = ap.parse_args()

    f = args.case / "system" / "blockMeshDict"
    text = f.read_text()
    text = replace_value(text, "cellsPerMetreX", args.x)
    text = replace_value(text, "cellsPerMetreY", args.y)
    text = replace_value(text, "cellsPerMetreZ", args.z)
    f.write_text(text)
    print(f"Updated {f}: cellsPerMetreX={args.x}, Y={args.y}, Z={args.z}")


if __name__ == "__main__":
    main()
