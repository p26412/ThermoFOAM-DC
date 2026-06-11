# v0.2 input CSV notes

`v02_generate_tables_and_plots.py` needs:

1. `metadata/v02_case_matrix.csv`, provided in this fixed bundle.
2. Either real OpenFOAM outputs under `cases/parameterstudy/C*/postProcessing/dcMetricsPlus/*/metrics.csv`, or a manual fallback summary file named `inputs/v02_global_summary_user.csv`.

If real OpenFOAM metrics exist, the script prefers them and does not need `v02_global_summary_user.csv`.
Optional files:

- `inputs/v02_per_rack_summary_user.csv` for per-rack heatmaps.
- `inputs/v02_yplus_table_user.csv` for y+ table copy-through.
- `inputs/v02_mesh_independence_reference_template.csv` for mesh-reference table copy-through.
