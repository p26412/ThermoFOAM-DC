<<<<<<< HEAD
#!/bin/sh
# Create grid_07, grid_10, grid_14 cases from the RNG k-epsilon baseline.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
=======
#!/usr/bin/env bash
# Create grid_07, grid_10, grid_14 cases from the RNG k-epsilon baseline.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
>>>>>>> aeb3467 (Release ThermoFOAM-DC v0.2 ten-case parameter-study workflow)
BASE="$ROOT/cases/01_baseline_RNGkEpsilon"
OUT="$ROOT/gridStudy_RNG"

mkdir -p "$OUT"

<<<<<<< HEAD
for cpm in 7 10 14; do
    caseName=$(printf "grid_%02d" "$cpm")
    dest="$OUT/$caseName"
    rm -rf "$dest"
    cp -r "$BASE" "$dest"
    python3 "$ROOT/scripts/set_cells_per_metre.py" "$dest/system/blockMeshDict" "$cpm" "$cpm" "$cpm"
=======
clean_generated_from_case() {
    local case_dir="$1"
    find "$case_dir" -mindepth 1 -maxdepth 1 -type d \
        \( -regex '.*/[1-9][0-9]*\(\.[0-9]*\)?' -o -name 'processor*' -o -name 'processors*' -o -name 'postProcessing' -o -name 'VTK' -o -name 'dynamicCode' -o -name 'platforms' \) \
        -exec rm -rf {} +
    find "$case_dir" -mindepth 1 -maxdepth 1 -type f \
        \( -name 'log.*' -o -name '*.log' -o -name '*.foam' -o -name '*.vtk' -o -name '*.vtu' -o -name '*.vtp' \) \
        -delete
}

for cpm in 7 10 14; do
    case_name="$(printf "grid_%02d" "$cpm")"
    dest="$OUT/$case_name"
    rm -rf "$dest"
    cp -a "$BASE" "$dest"
    clean_generated_from_case "$dest"
    python3 "$ROOT/scripts/set_cells_per_metre.py" "$dest" --x "$cpm" --y "$cpm" --z "$cpm"
>>>>>>> aeb3467 (Release ThermoFOAM-DC v0.2 ten-case parameter-study workflow)
    echo "Created $dest with cellsPerMetre = $cpm"
done
