# ThermoFOAM-DC v0.1

**OpenFOAM-based data-center cooling and hotspot analysis workflow**

ThermoFOAM-DC is a reproducible OpenFOAM workflow for studying simplified air-cooled data-center thermal management. Version 0.1 models a rectangular data-center room with rack heat-source zones, floor supply tiles, a return outlet, buoyancy-driven thermal transport, and RANS turbulence modelling.

This corrected v0.1 release uses **RNG k-epsilon as the primary turbulence model**. Standard k-epsilon and k-omega SST are retained as sensitivity setups, because turbulence models are not magical stickers one slaps onto a case and hopes peer review applauds.

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
```

---

## Repository structure

```text
cases/       OpenFOAM case setups
src/         dcMetricsPlus source code
scripts/     grid, metrics, plotting, v0.2 case generation, and y+ helper scripts
docs/        methodology and publication notes
results/     curated CSV tables and plots
environment/ OpenFOAM version/run notes
```

Generated OpenFOAM time folders, VTK files, logs, and build outputs are ignored by `.gitignore`.

---

## Current limitations

- racks are represented as heat-source zones, not detailed server cabinets
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
