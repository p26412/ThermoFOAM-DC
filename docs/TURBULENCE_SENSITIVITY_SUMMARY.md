# Turbulence model sensitivity summary

The corrected v0.1 primary turbulence model is **RNG k-epsilon**. Standard k-epsilon and k-omega SST are included as sensitivity setups.

## Why RNG k-epsilon is primary

All tested steady RANS models showed noticeable quasi-steady oscillation. RNG k-epsilon gave the best overall combination of:

- acceptable grid trends when late-time averages are used,
- strong y+ behavior on the uniform grid family,
- practical runtime,
- suitability for recirculating indoor/HVAC-type airflow.

## RNG k-epsilon late-average grid results

The reported values are averaged over:

```text
4000, 5000, 6000, 7000, 8000
```

| Grid | TavgRackInlet [K] | T95RackInlet [K] | TavgRoom [K] | T95Room [K] | Room hotspot fraction >315K | Rack risk fraction >305K | DeltaP [Pa] |
|---|---:|---:|---:|---:|---:|---:|---:|
| grid_07 | 302.957 | 313.911 | 307.129 | 314.169 | 0.0319 | 0.497 | 0.598 |
| grid_10 | 302.695 | 313.542 | 307.123 | 313.513 | 0.0161 | 0.481 | 0.566 |
| grid_14 | 302.040 | 311.928 | 306.728 | 312.944 | 0.00914 | 0.449 | 0.583 |

## Sensitivity setup included

```text
cases/02_baseline_kEpsilon_sensitivity
cases/03_baseline_kOmegaSST_sensitivity
```

These are retained for comparison and future documentation. The v0.2 full parameter sweep should use RNG k-epsilon only, with optional k-epsilon checks on the baseline and worst case.
