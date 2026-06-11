<<<<<<< HEAD
# ThermoFOAM-DC v0.1

**OpenFOAM-based data-center cooling and hotspot analysis workflow**

ThermoFOAM-DC is a reproducible OpenFOAM workflow for studying simplified air-cooled data-center thermal management. Version 0.1 models a rectangular data-center room with rack heat-source zones, floor supply tiles, a return outlet, buoyancy-driven thermal transport, and RANS turbulence modelling.

This v0.1 release adopts RNG k-epsilon as the primary turbulence model, selected from the grid-sensitivity and y+ verification study. Standard k-epsilon and k-omega SST setups are retained as sensitivity cases to compare the effect of turbulence-model choice on the cooling predictions.
---

## v0.1 scope

Included in this release:

- 3D simplified data-center room geometry
- six rack heat-source zones using `fvModels`
- floor-mounted cold-air supply tiles
- return outlet
- `foamRun -solver fluid` workflow for OpenFOAM Foundation v13 / openfoam-dev style cases
- **RNG k-epsilon primary baseline case**
- uniform structured grid study: `grid_07`, `grid_10`, `grid_14`
- late-iteration averaging for quasi-steady oscillatory RANS results
- y+ verification for wall-function consistency
- standard k-epsilon and k-omega SST sensitivity setups
- non-uniform mesh-layout sensitivity resources
- custom `dcMetricsPlus` post-processing utility
- curated result tables and plots

Deferred to v0.2:

- low/high supply velocity cases
- warmer supply air case
- high rack heat-load case
- overloaded rack case
- design trade-off plots and ranking

---

## Physical model

The v0.1 model uses a single fluid region representing room air. Racks are represented as heat-source cell zones rather than detailed solid cabinets. This is a deliberate baseline simplification.

Main physics:

- turbulent room airflow
- temperature transport
- buoyancy through Boussinesq thermodynamics
- rack heat sources
- wall-function RANS turbulence modelling

Primary turbulence model:

```text
RNGkEpsilon
```

Sensitivity models:

```text
kEpsilon
kOmegaSST
```

---

## Why late-iteration averages are used

The steady RANS solutions show noticeable quasi-steady oscillation in monitored thermal metrics. Therefore, v0.1 reports **late-iteration averaged metrics** over:

```text
4000, 5000, 6000, 7000, 8000
```

The final value at `8000` is treated as a supporting snapshot, not as divine truth. This is a CFD project, not a fortune cookie.

---

## Main engineering metrics

The custom `dcMetricsPlus` utility extracts:

- average rack-inlet temperature
- 95th percentile rack-inlet temperature
- maximum rack-inlet temperature
- rack-inlet risk fraction above 305 K
- average room temperature
- 95th percentile room temperature
- maximum room temperature
- room hotspot fraction above 315 K
- return outlet area-average temperature
- return outlet outflow-weighted temperature
- return outlet outflow flux
- pressure difference between supply and return

For grid independence, integrated/statistical quantities such as `TavgRackInlet`, `T95RackInlet`, `T95Room`, and hotspot fractions are emphasized over single-cell maxima.

---

## Key v0.1 verification result: RNG k-epsilon

The formal grid study uses the **uniform structured grid family** and late-iteration averages from `4000-8000`.

| Grid | Cells | hEff [m] | TavgRackInlet mean [K] | T95RackInlet mean [K] | Rack risk fraction T>305K | TavgRoom mean [K] | T95Room mean [K] | Room hotspot fraction T>315K | deltaP mean [Pa] | Role |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| grid_07 | 38,220 | 0.1401 | 302.957 | 313.911 | 0.497 | 307.129 | 314.169 | 0.0319 | 0.598 | coarse reference |
| grid_10 | 105,000 | 0.1000 | 302.695 | 313.542 | 0.481 | 307.123 | 313.513 | 0.0161 | 0.566 | production mesh candidate |
| grid_14 | 285,180 | 0.0717 | 302.040 | 311.928 | 0.449 | 306.728 | 312.944 | 0.00914 | 0.583 | fine-grid reference |

The fine grid was checked further because the minimum y+ was locally below 30. Only **8 out of 26,763 wall faces** were below y+ = 30, corresponding to **0.0299%** of wall faces. Therefore, the fine grid is acceptable as the reference grid for wall-function RANS.

---

## y+ verification: grid_14 RNG k-epsilon

| Patch | Faces | Faces with y+ < 30 | Percent below 30 | Min y+ | Avg y+ | Max y+ |
|---|---:|---:|---:|---:|---:|---:|
| floor | 6526 | 0 | 0.0000% | 32.1298 | 91.7744 | 160.0916 |
| ceiling | 6209 | 2 | 0.0322% | 27.4215 | 116.0299 | 183.3349 |
| walls | 14028 | 6 | 0.0428% | 27.4215 | 89.9197 | 266.7922 |
| total | 26763 | 8 | 0.0299% | - | - | - |

---

## Recommended mesh interpretation

- `grid_07`: coarse reference
- `grid_10`: practical production mesh candidate with low runtime
- `grid_14`: fine-grid reference with acceptable y+ distribution

For v0.2 parameter studies, use `grid_10` for the full sweep and rerun selected important cases on `grid_14` for verification.

---

## How to run the RNG baseline case

From the repository root:

```bash
cd cases/01_baseline_RNGkEpsilon
./Allclean
./Allrun
```

Compile the post-processing utility:

```bash
cd ../../src/dcMetricsPlus
wmake
```

Run metrics:

```bash
cd ../../cases/01_baseline_RNGkEpsilon
dcMetricsPlus
```

Run y+ verification:

```bash
foamPostProcess -solver fluid -func yPlus -latestTime
python3 ../../scripts/yplus_fraction.py 8000/yPlus 30
=======
# ThermoFOAM-DC v0.2

**OpenFOAM-based data-center cooling, hotspot, and parameter-study workflow**

ThermoFOAM-DC is a reproducible OpenFOAM workflow for studying simplified air-cooled data-center thermal management. Version 0.2 extends the verified v0.1 RNG k-epsilon baseline into a ten-case cooling parameter study covering supply velocity, supply temperature, rack heat load, overloaded-rack scenarios, pressure-flow proxy metrics, per-rack hotspot analysis, and CFD visualization outputs.

This repository is intended as an open engineering benchmark and research workflow, not a production-certified data-center digital twin.

---
## Version history

- **v0.1.0**: Baseline OpenFOAM data-center cooling workflow with grid sensitivity, y+ verification, turbulence-model sensitivity, and custom hotspot metrics.
- **v0.2.0**: Ten-case parametric cooling study with automated global/per-rack post-processing, pressure-flow proxy analysis, publication-style plots, and CFD contour/profile visualization.

Archived versions:
- v0.1.0: https://github.com/p26412/ThermoFOAM-DC/tree/v0.1.0
- v0.2.0: https://github.com/p26412/ThermoFOAM-DC/tree/v0.2.0


## v0.2 scope

Included in this release:

- simplified 3D data-center room with floor supply tiles, ceiling return, and six rack heat-source zones
- OpenFOAM Foundation v13 / `foamRun -solver fluid` style case setup
- RNG k-epsilon primary RANS workflow
- v0.1 grid, y+, and turbulence-model sensitivity documentation retained
- ten-case v0.2 parameter-study matrix
- automated case generator for C00-C09
- custom `dcMetricsPlus` post-processing utility
- global late-window tables and SVG plots
- optional per-rack table and heatmap generation from `dcMetricsPlus_perRack` outputs
- ParaView Python CFD figure generation
- filled contours with optional isolines
- line-profile CSV/SVG generation for `Ux`, `Uy`, `Uz`, `|U|`, `T`, `p_rgh`, `p`, `k`, `epsilon`, `omega`, `nut`, and `alphat` when available

---

## v0.2 case matrix

| Case | Folder | Description |
|---|---|---|
| C00 | `C00_baseline` | Six racks at 3 kW each, supply velocity 0.75 m/s, supply temperature 291 K |
| C01 | `C01_lowSupplyVelocity` | Baseline heat load, lower supply velocity 0.50 m/s |
| C02 | `C02_highSupplyVelocity` | Baseline heat load, higher supply velocity 1.00 m/s |
| C03 | `C03_warmerSupplyAir` | Baseline heat load, warmer supply temperature 295 K |
| C04 | `C04_highRackLoad` | All racks increased to 5 kW each |
| C05 | `C05_overloadedRack_L2` | Rack L2 overloaded to 8 kW, other racks at 3 kW |
| C06 | `C06_worstCase_lowFlow_highLoad` | Low flow with all racks at 5 kW |
| C07 | `C07_mitigation_highFlow_highLoad` | High-flow mitigation for all racks at 5 kW |
| C08 | `C08_overloadedRack_L2_lowFlow` | Overloaded L2 with low supply velocity |
| C09 | `C09_overloadedRack_L2_highFlow` | Overloaded L2 with high supply velocity |

The machine-readable case matrix is stored in:

```text
metadata/v02_case_matrix.csv
>>>>>>> aeb3467 (Release ThermoFOAM-DC v0.2 ten-case parameter-study workflow)
```

---

## Repository structure

```text
<<<<<<< HEAD
cases/       OpenFOAM case setups
src/         dcMetricsPlus source code
scripts/     grid, metrics, plotting, v0.2 case generation, and y+ helper scripts
docs/        methodology and publication notes
results/     curated CSV tables and plots
environment/ OpenFOAM version/run notes
```

Generated OpenFOAM time folders, VTK files, logs, and build outputs are ignored by `.gitignore`.
=======
ThermoFOAM-DC/
  cases/
    01_baseline_RNGkEpsilon/
    02_baseline_kEpsilon_sensitivity/
    03_baseline_kOmegaSST_sensitivity/
    parameterstudy/
      C00_baseline/
      C01_lowSupplyVelocity/
      ...
      C09_overloadedRack_L2_highFlow/
  scripts/
    create_parameter_cases_v02_10cases.py
    collect_per_rack_summary.py
    run_v02_analysis.sh
    v02_generate_tables_and_plots.py
    cfd_viz/
  src/
    dcMetricsPlus/
  metadata/
    v02_case_matrix.csv
  inputs/
    README.md
  docs/
  results/
    tables/
    plots/
```

Generated OpenFOAM time folders, `processor*` folders, logs, VTK output, ParaView `.foam` files, and build outputs are excluded by `.gitignore`.

---

## Requirements

Core CFD workflow:

```text
OpenFOAM Foundation v13 or compatible openfoam-dev style setup
Python 3
```

Optional visualization workflow:

```text
ParaView with pvpython, or python3-paraview
```

The table and SVG-plot scripts intentionally avoid NumPy, pandas, and matplotlib so that summary generation works on minimal HPC environments.

---

## Compile the custom metric utility

From the repository root:

```bash
source /opt/openfoam13/etc/bashrc
cd src/dcMetricsPlus
wmake
cd ../..
```

Adjust the OpenFOAM path if your installation is different.

---

## Generate the ten v0.2 cases

The release already includes generated C00-C09 case templates under `cases/parameterstudy`. To regenerate them from a baseline case:

```bash
python3 scripts/create_parameter_cases_v02_10cases.py \
  cases/01_baseline_RNGkEpsilon \
  cases/parameterstudy \
  --overwrite
```

For the full v0.2 sweep, the recommended production mesh is the grid-10 case from the v0.1 mesh study. If you have regenerated `gridStudy_RNG/grid_10`, use it as the base:

```bash
python3 scripts/create_parameter_cases_v02_10cases.py \
  gridStudy_RNG/grid_10 \
  cases/parameterstudy \
  --overwrite
```

---

## Run all ten cases

From the repository root:

```bash
source /opt/openfoam13/etc/bashrc
./Allrun cases/parameterstudy
```

Equivalent manual loop:

```bash
cd cases/parameterstudy
for case in C*/; do
    echo "Running $case"
    ( cd "$case" && ./Allclean && ./Allrun )
done
cd ../..
```

---

## Run or reuse `dcMetricsPlus`

If the simulations are already complete and you already have:

```text
postProcessing/dcMetricsPlus/0
postProcessing/dcMetricsPlus/1000
...
postProcessing/dcMetricsPlus/8000
```

then you do not need to rerun `dcMetricsPlus`.

To recompute global metrics over all saved times:

```bash
cd cases/parameterstudy
for case in C*/; do
    echo "Metrics $case"
    ( cd "$case" && dcMetricsPlus -time '0:8000' )
done
cd ../..
```

If your custom utility also writes per-rack metrics to:

```text
postProcessing/dcMetricsPlus_perRack/<rack>/<time>/metrics.csv
```

then the v0.2 analysis wrapper can automatically collect those into `inputs/v02_per_rack_summary_user.csv`.

---

## Generate v0.2 tables and publication SVG plots

Use a late-window average to avoid startup transient contamination:

```bash
bash scripts/run_v02_analysis.sh \
  --cases-root cases/parameterstudy \
  --late-start 4000
```

Expected global outputs:

```text
results/tables/v02_global_timeseries.csv
results/tables/v02_global_summary.csv
results/tables/v02_global_summary_compact.csv
results/tables/v02_flow_balance_table.csv
results/tables/v02_heat_balance_diagnostic_table.csv
results/tables/v02_main_findings.csv
results/plots/publication/Fig02_TavgRackInlet_mean_std.svg
results/plots/publication/Fig03_T95RackInlet_mean_std.svg
results/plots/publication/Fig04_rackRiskFraction_mean_std.svg
results/plots/publication/Fig05_roomHotspotFraction_mean_std.svg
results/plots/publication/Fig06_pressureFlowProxy_mean_std.svg
results/plots/publication/Fig07_pressureProxy_vs_T95RackInlet.svg
```

If per-rack data are available, additional outputs include:

```text
results/tables/v02_per_rack_summary.csv
results/tables/v02_per_rack_hotspot_ranking.csv
results/plots/publication/Fig08_perRack_Tavg_heatmap.svg
results/plots/publication/Fig09_perRack_T95_heatmap.svg
results/plots/publication/Fig12_perRack_risk_heatmap.svg
```

A root-level helper is also provided:

```bash
./Allpostprocess_v02 cases/parameterstudy 4000
```

---

## ParaView figure generation

Create `.foam` files:

```bash
bash scripts/cfd_viz/make_foam_files.sh cases/parameterstudy
```

Generate optional derived CFD fields at time 8000:

```bash
source /opt/openfoam13/etc/bashrc
bash scripts/cfd_viz/write_cfd_fields_all_cases.sh cases/parameterstudy 8000
```

Generate main ParaView CFD figures:

```bash
export PVPYTHON_BIN=pvpython
bash scripts/cfd_viz/run_pv_figures_all_cases.sh cases/parameterstudy 8000
```

Generate velocity/scalar contours with contour lines and profile plots:

```bash
export PVPYTHON_BIN=pvpython
PV_NUM_CONTOUR_LINES=18 PV_CONTOUR_LINE_WIDTH=1.5 \
bash scripts/cfd_viz/run_velocity_figures_all_cases.sh \
  cases/parameterstudy \
  8000 \
  results/plots/cfd_velocity_with_isolines
```

This produces filled contours, isolines, and profile plots for available fields such as:

```text
Ux, Uy, Uz, |U|, T, p_rgh, p, k, epsilon, omega, nut, alphat
```
>>>>>>> aeb3467 (Release ThermoFOAM-DC v0.2 ten-case parameter-study workflow)

---

## Current limitations

- racks are represented as heat-source zones, not detailed server cabinets
<<<<<<< HEAD
- no porous rack resistance in v0.1
- no experimental validation yet
- transient RANS was tested but was too expensive for this v0.1 workflow
- LES/hybrid RANS-LES are deferred to later high-fidelity work

---

## Roadmap

### v0.2

Add RNG k-epsilon design parameter studies:

- low supply velocity
- high supply velocity
- warmer supply air
- higher rack heat load
- one overloaded rack
- optional worst-case and mitigation cases

### v0.3

Add porous rack resistance and better rack airflow representation.

### v0.4

Add validation or benchmark comparison with published data-center cooling datasets.

### v1.0

Automated data-center cooling case generation, parametric sweeps, and design ranking.
=======
- no porous rack pressure-loss model in v0.2
- no experimentally validated data-center benchmark comparison yet
- pressure-flow proxy is a relative engineering metric, not a full fan-energy model
- per-rack post-processing depends on the availability of `dcMetricsPlus_perRack` outputs
- CHT, server fan curves, CRAH/CRAC coil models, and raised-floor plenum modelling are deferred

---

## Recommended interpretation

v0.2 is suitable as a GitHub engineering/research workflow showing:

- reproducible OpenFOAM case setup
- parametric CFD case generation
- automated hotspot metrics
- late-window statistical reporting
- per-rack hotspot comparison when available
- CFD visualization and line-profile extraction

For journal submission, v0.2 should be extended with validation, uncertainty analysis, selected fine-grid reruns, and improved physical realism.

---

## License

GPL-3.0-or-later.
>>>>>>> aeb3467 (Release ThermoFOAM-DC v0.2 ten-case parameter-study workflow)
