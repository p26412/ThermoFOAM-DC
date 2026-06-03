# Metrics used by `dcMetricsPlus`

## `TavgRackInlet`

Volume-weighted average temperature inside rack-inlet monitor boxes.

This is the main cooling-quality metric.

## `T95RackInlet`

Volume-weighted 95th percentile temperature in rack-inlet monitor boxes.

This is more robust than a raw maximum but still captures high-temperature risk.

## `TmaxRackInlet`

Maximum cell temperature inside rack-inlet monitor boxes.

Useful as a safety metric, but sensitive to isolated cells.

## `TavgRoom`

Volume-weighted average room temperature.

## `T95Room`

Volume-weighted 95th percentile room temperature.

## `roomHotspotVolumeFraction`

Fraction of the full room volume where:

```text
T > roomHotspotThreshold
```

Default threshold: `315 K`.

## `rackInletHotspotFraction`

Fraction of rack-inlet monitor-box volume where:

```text
T > rackInletRiskThreshold
```

Default threshold: `305 K`.

## `returnOutletTareaAvg`

Area-weighted return outlet temperature.

This can be sensitive if the return outlet has weak flow or recirculation.

## `returnOutletTmassFlowAvg`

Outflow-weighted return outlet temperature computed using positive `U dot Sf` flux through `returnOutlet`.

This is the preferred return-temperature metric.

## `deltaP_supply_minus_return`

Area-average pressure on supply patch minus area-average pressure on return patch.

Use consistently with the same pressure field, usually `p_rgh` for this v0.1 setup.
