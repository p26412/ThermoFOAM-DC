# Grid-independence plan for publication

Primary model for this release: **RNG k-epsilon**. Use late-iteration averages over 4000-8000 because the RANS solution shows quasi-steady oscillation.

## Meshes

Use:

```text
grid_07
grid_10
grid_14
```

Optional stronger check:

```text
grid_18
```

The mesh parameter is:

```text
hEff = (totalVolume / nCells)^(1/3)
```

## Primary quantities

Use:

```text
TavgRackInlet
T95RackInlet
TavgRoom
roomHotspotVolumeFraction
rackInletHotspotFraction
returnOutletOutflowFlux
deltaP_supply_minus_return
```

## Acceptance guidance

Fine-medium differences should ideally satisfy:

```text
TavgRackInlet < 0.5 K or < 1%
T95RackInlet < 1.0 K
TavgRoom < 0.5 K or < 1%
returnOutletTmassFlowAvg is useful but should be treated as secondary if outlet recirculation is present
roomHotspotVolumeFraction < 0.03 absolute
rackInletHotspotFraction < 0.03 absolute
deltaP difference < 5% preferred; report as secondary if more sensitive
```

## What if convergence is non-monotonic?

Do not fake a GCI result. Use one of these actions:

1. use more robust metrics,
2. run a finer grid,
3. improve iterative convergence,
4. check turbulence model sensitivity,
5. report the mesh-sensitivity spread instead of claiming asymptotic convergence.

## Recommended plots

```text
TavgRackInlet vs hEff
T95RackInlet vs hEff
TmaxRackInlet vs hEff
TavgRoom vs hEff
returnOutletTmassFlowAvg vs hEff
roomHotspotVolumeFraction vs hEff
rackInletHotspotFraction vs hEff
deltaP_supply_minus_return vs hEff
runtime vs nCells
```
