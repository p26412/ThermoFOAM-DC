#!/bin/sh
# Create grid_07, grid_10, grid_14 cases from the RNG k-epsilon baseline.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
BASE="$ROOT/cases/01_baseline_RNGkEpsilon"
OUT="$ROOT/gridStudy_RNG"

mkdir -p "$OUT"

for cpm in 7 10 14; do
    caseName=$(printf "grid_%02d" "$cpm")
    dest="$OUT/$caseName"
    rm -rf "$dest"
    cp -r "$BASE" "$dest"
    python3 "$ROOT/scripts/set_cells_per_metre.py" "$dest/system/blockMeshDict" "$cpm" "$cpm" "$cpm"
    echo "Created $dest with cellsPerMetre = $cpm"
done
