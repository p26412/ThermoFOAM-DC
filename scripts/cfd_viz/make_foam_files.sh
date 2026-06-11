#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(pwd)}"
cd "$ROOT"

for d in C*/; do
    [ -d "$d/system" ] || continue
    caseName="${d%/}"
    touch "$caseName/$caseName.foam"
    echo "created/updated: $caseName/$caseName.foam"
done
