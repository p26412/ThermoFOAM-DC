#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-.}"
TIME_VALUE="${2:-8000}"

ROOT_DIR="$(cd "$ROOT_DIR" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PVPYTHON_BIN="${PVPYTHON_BIN:-python3}"
ONE_CASE_SCRIPT="$SCRIPT_DIR/pv_make_cfd_figures_one_case.py"

echo "Using ParaView Python command: $PVPYTHON_BIN"
"$PVPYTHON_BIN" --version || true

"$PVPYTHON_BIN" -c "import sys; print('Executable:', sys.executable); print('Version:', sys.version); import paraview.simple as pvs; print('ParaView Python import OK')" || {
    echo "ERROR: The selected Python command cannot import paraview.simple."
    echo
    echo "Tried:"
    echo "  $PVPYTHON_BIN"
    echo
    echo "Fix options:"
    echo "  1. sudo apt install --reinstall paraview python3-paraview"
    echo "  2. export PVPYTHON_BIN=/opt/ParaView/bin/pvpython"
    echo "  3. If python3 can import paraview.simple, use: export PVPYTHON_BIN=python3"
    exit 1
}

if [ ! -f "$ONE_CASE_SCRIPT" ]; then
    echo "ERROR: Missing ParaView case plotting script:"
    echo "  $ONE_CASE_SCRIPT"
    echo
    echo "Create this file first: scripts/cfd_viz/pv_make_cfd_figures_one_case.py"
    exit 1
fi

OUT_ROOT="$ROOT_DIR/results/plots/cfd_figures"
mkdir -p "$OUT_ROOT"

echo
echo "Root directory:"
echo "  $ROOT_DIR"
echo "Output directory:"
echo "  $OUT_ROOT"
echo "Requested time:"
echo "  $TIME_VALUE"
echo

case_count=0
success_count=0
fail_count=0

for CASE_DIR in "$ROOT_DIR"/C*/; do
    [ -d "$CASE_DIR" ] || continue

    CASE_NAME="$(basename "$CASE_DIR")"

    if [ ! -d "$CASE_DIR/system" ] || [ ! -d "$CASE_DIR/constant" ]; then
        echo "Skipping $CASE_NAME: not an OpenFOAM case folder"
        continue
    fi

    case_count=$((case_count + 1))

    FOAM_FILE="$CASE_DIR/${CASE_NAME}.foam"
    touch "$FOAM_FILE"

    CASE_OUT="$OUT_ROOT/$CASE_NAME"
    mkdir -p "$CASE_OUT"

    echo "============================================================"
    echo "Generating CFD figures for: $CASE_NAME"
    echo "Case directory: $CASE_DIR"
    echo "Foam file:      $FOAM_FILE"
    echo "Output:         $CASE_OUT"
    echo "============================================================"

    if "$PVPYTHON_BIN" "$ONE_CASE_SCRIPT" \
        --case "$CASE_DIR" \
        --time "$TIME_VALUE" \
        --out "$CASE_OUT"; then

        echo "OK: figures generated for $CASE_NAME"
        success_count=$((success_count + 1))
    else
        echo "WARNING: figure generation failed for $CASE_NAME"
        fail_count=$((fail_count + 1))
    fi

    echo
done

echo "============================================================"
echo "ParaView CFD figure generation summary"
echo "Cases found:     $case_count"
echo "Cases succeeded: $success_count"
echo "Cases failed:    $fail_count"
echo "Output folder:   $OUT_ROOT"
echo "============================================================"

if [ "$case_count" -eq 0 ]; then
    echo "ERROR: No OpenFOAM case folders found under:"
    echo "  $ROOT_DIR"
    echo
    echo "Expected folders like:"
    echo "  C00_baseline"
    echo "  C01_lowSupplyVelocity"
    echo "  C02_highSupplyVelocity"
    exit 1
fi

if [ "$success_count" -eq 0 ]; then
    echo "ERROR: No CFD figures were generated successfully."
    exit 1
fi
