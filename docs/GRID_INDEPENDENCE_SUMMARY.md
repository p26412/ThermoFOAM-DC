# Grid independence summary: RNG k-epsilon primary model

The corrected v0.1 grid-independence study uses the **uniform structured grid family** and **RNG k-epsilon** as the primary turbulence model.

The monitored results showed quasi-steady oscillation for all tested RANS models. Therefore, the grid study reports late-iteration averages over:

```text
4000, 5000, 6000, 7000, 8000
```

This is more defensible than reporting a single final-time value.

## Mesh family

| Grid | Cells | hEff [m] | Role |
|---|---:|---:|---|
| grid_07 | 38,220 | 0.1401 | coarse reference |
| grid_10 | 105,000 | 0.1000 | production candidate |
| grid_14 | 285,180 | 0.0717 | fine-grid reference |

The refinement ratio is approximately 1.4 between grid levels, which is suitable for a structured grid-sensitivity study.

## Primary grid metrics

Use these as primary quantities:

- `TavgRackInlet`
- `T95RackInlet`
- `rackRiskFraction305`
- `TavgRoom`
- `T95Room`
- `roomHotspotFraction315`
- `returnOutletOutflowFlux`

Use these as secondary quantities:

- `TmaxRackInlet`
- `TmaxRoom`
- `returnOutletTmassFlowAvg`
- `deltaP_supply_minus_return`

Maximum values and return/outlet quantities are more sensitive to local flow structure and should not be the only basis for mesh selection.

## Main result table

See:

```text
results/tables/grid_independence_uniform_RNGkEpsilon_late_average.csv
```

The main thermal metrics improve or remain reasonably stable with mesh refinement. The fine grid is accepted as the reference grid. The medium grid is recommended as the practical production mesh for v0.2 parameter studies.
