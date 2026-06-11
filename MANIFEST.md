<<<<<<< HEAD
# Manifest

This package is the corrected RNG-k-epsilon-primary GitHub-ready release.

## Primary case

```text
cases/01_baseline_RNGkEpsilon
```

## Sensitivity cases

```text
cases/02_baseline_kEpsilon_sensitivity
cases/03_baseline_kOmegaSST_sensitivity
```

## Main result files

```text
results/tables/grid_independence_uniform_RNGkEpsilon_late_average.csv
results/tables/yplus_uniform_RNGkEpsilon.csv
results/tables/yplus_fraction_grid14_uniform_RNGkEpsilon.csv
results/tables/v02_parameter_plan_RNGkEpsilon.csv
```

## Main scripts

```text
scripts/yplus_fraction.py
scripts/create_parameter_cases.py
scripts/collect_metrics_plus.py
scripts/plot_grid_independence_plus.py
```
=======
# ThermoFOAM-DC v0.2 manifest

## Top-level files

```text
README.md
LICENSE
CITATION.cff
.gitignore
Allrun
Allclean
Allpostprocess_v02
```

## Main folders

```text
cases/                    OpenFOAM baseline, sensitivity, and v0.2 parameter-study case templates
configs/                  configuration notes/resources from v0.1
docs/                     methodology, run commands, release notes, and publication plan
environment/              OpenFOAM environment/version notes
inputs/                   optional CSV inputs and fallback files for analysis scripts
metadata/                 v0.2 case matrix
results/                  curated result tables and figures; raw OpenFOAM outputs are excluded
scripts/                  case generation, post-processing, plotting, and ParaView scripts
src/dcMetricsPlus/        custom OpenFOAM metric utility source
```

## v0.2 parameter-study cases

```text
cases/parameterstudy/C00_baseline
cases/parameterstudy/C01_lowSupplyVelocity
cases/parameterstudy/C02_highSupplyVelocity
cases/parameterstudy/C03_warmerSupplyAir
cases/parameterstudy/C04_highRackLoad
cases/parameterstudy/C05_overloadedRack_L2
cases/parameterstudy/C06_worstCase_lowFlow_highLoad
cases/parameterstudy/C07_mitigation_highFlow_highLoad
cases/parameterstudy/C08_overloadedRack_L2_lowFlow
cases/parameterstudy/C09_overloadedRack_L2_highFlow
```

## Main v0.2 scripts

```text
scripts/create_parameter_cases_v02_10cases.py
scripts/collect_per_rack_metrics_v02.py
scripts/run_v02_analysis.sh
scripts/v02_generate_tables_and_plots.py
scripts/cfd_viz/make_foam_files.sh
scripts/cfd_viz/write_cfd_fields_all_cases.sh
scripts/cfd_viz/run_pv_figures_all_cases.sh
scripts/cfd_viz/run_velocity_figures_all_cases.sh
scripts/cfd_viz/plot_cfd_field_profiles_svg.py
```

## Notes

This archive intentionally excludes raw solved time folders, `processor*` folders, dynamic code builds, logs, VTK exports, and `.foam` files. Use the scripts to regenerate those locally.
>>>>>>> aeb3467 (Release ThermoFOAM-DC v0.2 ten-case parameter-study workflow)
