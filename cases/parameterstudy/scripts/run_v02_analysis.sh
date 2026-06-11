#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
python3 scripts/v02_generate_tables_and_plots.py --project-root "$PWD" "$@"
