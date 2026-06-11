#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:-.}"
TIME_VALUE="${2:-8000}"
OUT_ROOT_ARG="${3:-results/plots/cfd_velocity}"

ROOT_DIR="$(cd "$ROOT_DIR" && pwd)"
if [[ "$OUT_ROOT_ARG" = /* ]]; then
    OUT_ROOT="$OUT_ROOT_ARG"
else
    OUT_ROOT="$ROOT_DIR/$OUT_ROOT_ARG"
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prefer user override, then python3 with python3-paraview, then pvpython.
if [ -n "${PVPYTHON_BIN:-}" ]; then
    PV_CMD="$PVPYTHON_BIN"
elif python3 -c "import paraview.simple" >/dev/null 2>&1; then
    PV_CMD="python3"
elif command -v pvpython >/dev/null 2>&1; then
    PV_CMD="pvpython"
else
    echo "ERROR: neither python3-paraview nor pvpython is available."
    echo "Try one of these:"
    echo "  sudo apt install paraview python3-paraview"
    echo "  export PVPYTHON_BIN=/path/to/pvpython"
    exit 1
fi

echo "Using ParaView Python command: $PV_CMD"
"$PV_CMD" -c "import sys; print('Executable:', sys.executable); import paraview.simple as pvs; print('ParaView import OK')" || {
    echo "ERROR: selected Python command cannot import paraview.simple"
    echo "Selected command: $PV_CMD"
    exit 1
}

mkdir -p "$OUT_ROOT"

PV_ARGS=(
    "--num-contour-lines" "${PV_NUM_CONTOUR_LINES:-12}"
    "--contour-line-width" "${PV_CONTOUR_LINE_WIDTH:-1.25}"
)

if [ "${PV_NO_CONTOUR_LINES:-0}" = "1" ]; then
    PV_ARGS+=("--no-contour-lines")
fi

if [ -n "${PV_IMAGE_WIDTH:-}" ]; then
    PV_ARGS+=("--width" "$PV_IMAGE_WIDTH")
fi
if [ -n "${PV_IMAGE_HEIGHT:-}" ]; then
    PV_ARGS+=("--height" "$PV_IMAGE_HEIGHT")
fi
if [ -n "${PV_PROFILE_RESOLUTION:-}" ]; then
    PV_ARGS+=("--profile-resolution" "$PV_PROFILE_RESOLUTION")
fi

echo
echo "Root directory:        $ROOT_DIR"
echo "Output folder:         $OUT_ROOT"
echo "Requested time:        $TIME_VALUE"
echo "Contour lines:         $([ "${PV_NO_CONTOUR_LINES:-0}" = "1" ] && echo disabled || echo enabled)"
echo "Number contour lines:  ${PV_NUM_CONTOUR_LINES:-12}"
echo "Contour line width:    ${PV_CONTOUR_LINE_WIDTH:-1.25}"
echo

mapfile -t CASE_DIRS < <(find "$ROOT_DIR" -maxdepth 1 -mindepth 1 -type d -name 'C[0-9][0-9]*' | sort)

if [ "${#CASE_DIRS[@]}" -eq 0 ]; then
    echo "ERROR: no case directories found. Expected folders like C00_baseline, C01_lowSupplyVelocity, etc."
    exit 1
fi

ok_count=0
fail_count=0

for CASE_DIR in "${CASE_DIRS[@]}"; do
    CASE_NAME="$(basename "$CASE_DIR")"
    CASE_OUT="$OUT_ROOT/$CASE_NAME"
    echo "============================================================"
    echo "Generating CFD velocity/scalar plots for: $CASE_NAME"
    echo "Case:   $CASE_DIR"
    echo "Output: $CASE_OUT"
    echo "============================================================"

    if "$PV_CMD" "$SCRIPT_DIR/pv_make_velocity_figures_one_case.py" "$CASE_DIR" "$CASE_OUT" "$TIME_VALUE" "${PV_ARGS[@]}"; then
        if python3 "$SCRIPT_DIR/plot_velocity_profiles_svg.py" "$CASE_OUT/profiles"; then
            true
        else
            echo "WARNING: basic velocity profile SVG generation failed for $CASE_NAME, but contour plots may still exist."
        fi

        if python3 "$SCRIPT_DIR/plot_cfd_field_profiles_svg.py" "$CASE_OUT/profiles"; then
            true
        else
            echo "WARNING: CFD field profile SVG generation failed for $CASE_NAME, but contour plots may still exist."
        fi

        ok_count=$((ok_count + 1))
    else
        echo "WARNING: CFD plot generation failed for $CASE_NAME"
        fail_count=$((fail_count + 1))
    fi
    echo

done

echo "============================================================"
echo "CFD velocity/scalar plot generation summary"
echo "Cases found:     ${#CASE_DIRS[@]}"
echo "Cases succeeded: $ok_count"
echo "Cases failed:    $fail_count"
echo "Output folder:   $OUT_ROOT"
echo "============================================================"
