# LinkedIn post draft

I’m sharing **ThermoFOAM-DC v0.1**, an OpenFOAM-based CFD workflow for air-cooled data-center thermal analysis.

The project models a simplified data-center room with rack heat-source zones, floor supply tiles, return outlet flow, buoyancy-driven thermal transport, and RANS turbulence modelling.

For this first version, I focused on reproducibility and verification rather than only posting contour plots. The repository includes:

- RNG k-epsilon baseline setup
- uniform grid-independence study
- y+ verification for wall-function consistency
- custom `dcMetricsPlus` post-processing utility
- rack-inlet and room hotspot metrics
- turbulence-model sensitivity setup
- mesh-layout sensitivity resources
- result tables and plots

Main metrics include average and 95th percentile rack-inlet temperature, rack inlet risk fraction above 305 K, room hotspot fraction above 315 K, return outflow flux, and pressure difference.

A key verification detail: on the fine grid, only 8 out of 26,763 wall faces were below y+ = 30, corresponding to 0.0299% of wall faces. This supports the wall-function RANS setup.

Next step: v0.2 will add cooling design parameter studies, including supply velocity, warmer supply air, high rack load, and overloaded rack cases.

GitHub: <paste your repo link here>
