# Changelog

## v0.2.0

Released the ten-case ThermoFOAM-DC parameter-study workflow.

### Added
- Ten data-center cooling/load scenarios.
- Global hotspot metric analysis.
- Per-rack metric support.
- Publication-style summary plots.
- CFD contour figures with isolines.
- Line-profile plotting for Ux, Uy, Uz, |U|, T, pressure, and turbulence quantities.
- v0.2 case metadata file.
- Analysis and visualization run scripts.

### Changed
- Extended the v0.1 baseline workflow into a reproducible parameter-study framework.
- Improved post-processing documentation and run commands.

### Known limitations
- Experimental validation is not yet included.
- Rack regions are simplified heat-source zones.
- Fan power is currently represented using a pressure-flow proxy.
- Porous rack resistance is planned for v0.3.

## v0.1.0

Initial OpenFOAM baseline release.

### Added
- RNG k-epsilon baseline data-center room case.
- Standard k-epsilon and k-omega SST turbulence sensitivity cases.
- Grid sensitivity study.
- y+ verification.
- Custom `dcMetricsPlus` utility.
- Initial hotspot and room-temperature metrics.
