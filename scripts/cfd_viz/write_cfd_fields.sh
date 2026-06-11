#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: bash scripts/cfd_viz/write_cfd_fields.sh <caseDir> [timeMode]"
    echo "Example: bash scripts/cfd_viz/write_cfd_fields.sh C00_baseline latestTime"
    exit 1
fi

CASE_DIR="$1"
TIME_MODE="${2:-latestTime}"

if [ ! -d "$CASE_DIR" ]; then
    echo "ERROR: case directory not found: $CASE_DIR" >&2
    exit 1
fi

if command -v foamPostProcess >/dev/null 2>&1; then
    POST="foamPostProcess"
elif command -v postProcess >/dev/null 2>&1; then
    POST="postProcess"
else
    echo "ERROR: neither foamPostProcess nor postProcess found. Source your OpenFOAM bashrc first." >&2
    exit 1
fi

case "$TIME_MODE" in
    latestTime) TIME_FLAG="-latestTime" ;;
    allTime|allTimes) TIME_FLAG="" ;;
    *) TIME_FLAG="-time $TIME_MODE" ;;
esac

run_func() {
    local func="$1"
    echo "--- $CASE_DIR: computing $func"
    # shellcheck disable=SC2086
    if ! (cd "$CASE_DIR" && $POST -solver fluid $TIME_FLAG -func "$func"); then
        echo "WARNING: $func failed for $CASE_DIR. Continuing. Check whether this OpenFOAM version/model supports it." >&2
    fi
}

# Essential derived fields for CFD visualisation
run_func vorticity
run_func Q
run_func yPlus
run_func wallShearStress

# Thermal-wall diagnostics. This may not be available for every heRhoThermo/Boussinesq setup.
run_func wallHeatFlux

# Make ParaView reader file.
caseName="$(basename "$CASE_DIR")"
touch "$CASE_DIR/$caseName.foam"

echo "Done: $CASE_DIR"
