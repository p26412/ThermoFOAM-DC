#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(pwd)}"
TIME_MODE="${2:-latestTime}"
cd "$ROOT"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

count=0
for d in C*/; do
    [ -d "$d/system" ] || continue
    bash "$SCRIPT_DIR/write_cfd_fields.sh" "${d%/}" "$TIME_MODE"
    count=$((count + 1))
done

echo "Processed $count cases."
