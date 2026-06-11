# v0.2 parameter study plan

v0.2 should extend v0.1 from a verified baseline workflow into an engineering parameter study.

## Primary setup

```text
Turbulence model: RNGkEpsilon
Mesh for full sweep: uniform grid_10
Verification mesh: uniform grid_14 for selected important cases
Averaging: late-iteration mean and standard deviation over 4000-8000
```

## Core cases

| Case ID | Case name | Supply velocity [m/s] | Supply T [K] | Total heat [kW] | Rack pattern | Purpose |
|---|---|---:|---:|---:|---|---|
| C00 | baseline | 0.75 | 291 | 18 | all racks 3 kW | reference |
| C01 | lowSupplyVelocity | 0.50 | 291 | 18 | all racks 3 kW | airflow reduction risk |
| C02 | highSupplyVelocity | 1.00 | 291 | 18 | all racks 3 kW | stronger cooling / pressure penalty |
| C03 | warmerSupplyAir | 0.75 | 295 | 18 | all racks 3 kW | warmer supply operation |
| C04 | highRackLoad | 0.75 | 291 | 30 | all racks 5 kW | high IT heat density |
| C05 | overloadedRack_L2 | 0.75 | 291 | 23 | rack_L2 = 8 kW; others 3 kW | local hotspot risk |

## Optional cases

| Case ID | Case name | Supply velocity [m/s] | Supply T [K] | Total heat [kW] | Purpose |
|---|---|---:|---:|---:|---|
| C06 | worstCase_lowFlow_highLoad | 0.50 | 291 | 30 | worst thermal stress |
| C07 | mitigation_highFlow_highLoad | 1.00 | 291 | 30 | airflow mitigation check |

## What to report

For every case, report:

- `TavgRackInlet_mean ± std`
- `T95RackInlet_mean ± std`
- `rackRiskFraction305_mean ± std`
- `TavgRoom_mean ± std`
- `T95Room_mean ± std`
- `roomHotspotFraction315_mean ± std`
- `returnOutletTmassFlowAvg_mean ± std`
- `returnOutletOutflowFlux_mean ± std`
- `deltaP_mean ± std`

## Best plots for LinkedIn and GitHub

- `T95RackInlet` by case
- `rackRiskFraction305` by case
- `roomHotspotFraction315` by case
- `deltaP` by case
- trade-off plot: rack risk vs deltaP
- contour image for overloaded rack case
<<<<<<< HEAD

## Recommended release strategy

Release v0.1 first. Then use v0.2 as a clean follow-up release focused on design parameters and trade-offs.
=======
>>>>>>> aeb3467 (Release ThermoFOAM-DC v0.2 ten-case parameter-study workflow)
