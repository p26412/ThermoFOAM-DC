# GitHub upload guide

This repository is prepared as a lightweight public GitHub project. It uses **RNG k-epsilon as the primary v0.1 model**.

## Before upload

Check this list:

```text
[ ] README says RNG k-epsilon is the primary model
[ ] GitHub username replaced in CITATION.cff if desired
[ ] GitHub link replaced in docs/LINKEDIN_POST_DRAFT.md
[ ] no OpenFOAM time folders committed
[ ] no VTK folders committed
[ ] no huge logs committed
[ ] results/tables are present
[ ] results/plots are present
[ ] cases/01_baseline_RNGkEpsilon is present
[ ] cases/02_baseline_kEpsilon_sensitivity is present
[ ] cases/03_baseline_kOmegaSST_sensitivity is present
[ ] src/dcMetricsPlus is present
[ ] scripts/yplus_fraction.py is present
```

## Initialize Git

From the repository root:

```bash
git init
git add .
git status
```

Make sure you do **not** see generated OpenFOAM time folders such as:

```text
1000/
2000/
8000/
processor*/
dynamicCode/
VTK/
```

If the status is clean and sensible:

```bash
git commit -m "Initial ThermoFOAM-DC v0.1 RNG release"
```

## Create GitHub repo

Create an empty GitHub repository named:

```text
ThermoFOAM-DC
```

Do not initialize it with README, license, or gitignore. This local folder already has those files.

Then push:

```bash
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ThermoFOAM-DC.git
git push -u origin main
```

## Recommended release

Create a GitHub release:

```text
v0.1.0
```

Release title:

```text
ThermoFOAM-DC v0.1.0: RNG k-epsilon data-center cooling CFD workflow
```

Release notes:

```markdown
Initial public release of ThermoFOAM-DC.

Included:
- RNG k-epsilon primary OpenFOAM baseline setup
- uniform grid-independence study
- late-iteration averaged metrics for quasi-steady RANS behavior
- y+ verification and y+ face-fraction check
- dcMetricsPlus post-processing utility
- standard k-epsilon and k-omega SST sensitivity setups
- v0.2 parameter-study plan
```
