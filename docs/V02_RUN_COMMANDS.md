# ThermoFOAM-DC v0.2 run commands

This page summarizes the commands for a completed ten-case v0.2 parameter study.

## 1. From repository root

```bash
cd ThermoFOAM-DC
source /opt/openfoam13/etc/bashrc
```

## 2. Compile metric utility

```bash
cd src/dcMetricsPlus
wmake
cd ../..
```

## 3. Run the ten OpenFOAM cases

```bash
./Allrun cases/parameterstudy
```

Manual equivalent:

```bash
cd cases/parameterstudy
for case in C*/; do
    echo "Running $case"
    ( cd "$case" && ./Allclean && ./Allrun )
done
cd ../..
```

## 4. Compute global dcMetricsPlus metrics

Skip this step if these folders already exist:

```text
postProcessing/dcMetricsPlus/0
postProcessing/dcMetricsPlus/1000
...
postProcessing/dcMetricsPlus/8000
```

Otherwise run:

```bash
cd cases/parameterstudy
for case in C*/; do
    echo "Metrics $case"
    ( cd "$case" && dcMetricsPlus -time '0:8000' )
done
cd ../..
```

## 5. Generate v0.2 tables and publication SVG plots

```bash
bash scripts/run_v02_analysis.sh --cases-root cases/parameterstudy --late-start 4000
```

or:

```bash
./Allpostprocess_v02 cases/parameterstudy 4000
```

## 6. Create ParaView `.foam` files

```bash
bash scripts/cfd_viz/make_foam_files.sh cases/parameterstudy
```

## 7. Optional derived fields

```bash
bash scripts/cfd_viz/write_cfd_fields_all_cases.sh cases/parameterstudy 8000
```

## 8. Main ParaView CFD figures

```bash
export PVPYTHON_BIN=pvpython
bash scripts/cfd_viz/run_pv_figures_all_cases.sh cases/parameterstudy 8000
```

## 9. Velocity/scalar contour figures with isolines and profile plots

```bash
export PVPYTHON_BIN=pvpython
PV_NUM_CONTOUR_LINES=18 PV_CONTOUR_LINE_WIDTH=1.5 \
bash scripts/cfd_viz/run_velocity_figures_all_cases.sh \
  cases/parameterstudy \
  8000 \
  results/plots/cfd_velocity_with_isolines
```

## 10. Check outputs

```bash
ls results/tables
ls results/plots/publication
find results/plots/cfd_velocity_with_isolines -name '*.png' | head
find results/plots/cfd_velocity_with_isolines -name '*.svg' | head
```
