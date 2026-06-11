# v0.2 CFD visualization patch: contour lines + field profile line plots

This patch updates the velocity/CFD visualization workflow.

## Updated files

- `scripts/cfd_viz/run_velocity_figures_all_cases.sh`
- `scripts/cfd_viz/pv_make_velocity_figures_one_case.py`
- `scripts/cfd_viz/plot_cfd_field_profiles_svg.py` new

## What changed

1. Filled contour PNGs now include black isoline overlays by default.
2. The ParaView script also attempts extra scalar contour fields when available:
   - `T`
   - `p_rgh`
   - `p`
   - `k`
   - `epsilon`
   - `omega`
   - `nut`
   - `alphat`
3. Profile CSVs are now written for more line locations:
   - room centerline in x
   - room centerline in y
   - room centerline in z
   - near-floor x line
   - rack-height x line
   - near-ceiling x line
   - supply-to-return diagonal
4. SVG line plots are generated for:
   - `Ux / u`
   - `Uy / v`
   - `Uz / w`
   - `|U|`
   - `T`
   - `p`, `p_rgh`
   - `k`, `epsilon`, `omega`, `nut`, `alphat`, and other numeric scalar columns when present

## Main command

From inside the folder that contains `C00_baseline`, `C01_lowSupplyVelocity`, etc.:

```bash
chmod +x scripts/cfd_viz/*.sh scripts/cfd_viz/*.py
export PVPYTHON_BIN=pvpython
bash scripts/cfd_viz/run_velocity_figures_all_cases.sh "$PWD" 8000
```

## More contour lines

```bash
export PVPYTHON_BIN=pvpython
PV_NUM_CONTOUR_LINES=18 PV_CONTOUR_LINE_WIDTH=1.5 \
  bash scripts/cfd_viz/run_velocity_figures_all_cases.sh "$PWD" 8000
```

## Save to a new folder instead of overwriting old output

```bash
export PVPYTHON_BIN=pvpython
PV_NUM_CONTOUR_LINES=18 PV_CONTOUR_LINE_WIDTH=1.5 \
  bash scripts/cfd_viz/run_velocity_figures_all_cases.sh "$PWD" 8000 results/plots/cfd_velocity_with_isolines
```

## Disable contour lines

```bash
PV_NO_CONTOUR_LINES=1 bash scripts/cfd_viz/run_velocity_figures_all_cases.sh "$PWD" 8000
```

## Only regenerate line plots from already-written profile CSVs

```bash
for d in results/plots/cfd_velocity/C*/profiles; do
    python3 scripts/cfd_viz/plot_cfd_field_profiles_svg.py "$d"
done
```

## Outputs

Contour PNGs:

```text
results/plots/cfd_velocity/<case>/contours/
```

Profile CSVs:

```text
results/plots/cfd_velocity/<case>/profiles/
```

Line-plot SVGs:

```text
results/plots/cfd_velocity/<case>/profiles/line_plots/
```
