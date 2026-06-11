# ThermoFOAM-DC v0.2 release notes

## Summary

ThermoFOAM-DC v0.2 converts the v0.1 RNG k-epsilon verified baseline into a ten-case data-center cooling parameter study. The release focuses on reproducibility, post-processing automation, CFD figure generation, and hotspot-oriented engineering metrics.

## New in v0.2

- ten-case parameter-study matrix C00-C09
- automated v0.2 case generator
- late-window table and SVG figure generation
- pressure-flow proxy and heat-removal diagnostic tables
- automatic per-rack summary collection when `dcMetricsPlus_perRack` outputs exist
- ParaView figure scripts for all cases
- velocity/scalar contour plots with isoline overlays
- line-profile CSV/SVG generation for velocity components, temperature, pressure, and turbulence quantities
- root-level `Allrun`, `Allclean`, and `Allpostprocess_v02` helpers

## Case matrix

See:

```text
metadata/v02_case_matrix.csv
```

## Main commands

```bash
./Allrun cases/parameterstudy
./Allpostprocess_v02 cases/parameterstudy 4000
```

## Status

This version is suitable for public GitHub release as a reproducible OpenFOAM engineering workflow. Journal submission should wait until the additional validation and uncertainty-analysis work listed in `docs/PUBLICATION_JOURNAL_PLAN.md` is complete.
