# Turbulence model plan

## v0.1 conclusion

Based on the grid-independence behavior and y+ checks, the corrected primary model is:

```text
RNGkEpsilon
```

Standard `kEpsilon` and `kOmegaSST` are retained as sensitivity setups, not as the main v0.1 model.

## Why RNG k-epsilon is selected

The tested steady RANS models all showed quasi-steady oscillation in monitored metrics. RNG k-epsilon gave the most practical combination of:

- acceptable grid trend using late-time averages,
- strong y+ behavior on the uniform grid family,
- good suitability for recirculating indoor/HVAC-type flow,
- manageable runtime.

## What not to do in v0.2

Do not run every parameter case with every turbulence model. That becomes a simulation hostage crisis.

Recommended v0.2 approach:

```text
Main parameter sweep: RNGkEpsilon
Optional sensitivity: kEpsilon only for baseline and worst case
Archive/reference: kOmegaSST from v0.1
```

LES, DES, IDDES, and hybrid methods are future high-fidelity work, not the v0.2 workflow.
