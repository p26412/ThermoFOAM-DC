# Publication-style workflow

Use `cases/01_baseline_RNGkEpsilon` as the primary baseline case.

## Recommended sequence

1. Run the RNG k-epsilon baseline on the uniform mesh family.
2. Use late-iteration averages over 4000-8000 because the steady RANS solution shows quasi-steady oscillation.
3. Check y+ on all wall patches.
4. Use `grid_10` as the practical production mesh candidate.
5. Use `grid_14` as the fine-grid reference.
6. Keep standard k-epsilon and k-omega SST as sensitivity setups.
7. Do not claim validation until an experimental/literature benchmark comparison is added.

## Main claim allowed in v0.1

```text
This repository provides a reproducible OpenFOAM workflow for data-center cooling CFD with grid sensitivity, y+ verification, and turbulence-model sensitivity.
```

## Claims to avoid

```text
validated industrial optimizer
production-ready digital twin
LES-grade high-fidelity model
```

Apparently words are expected to mean things. Inconvenient, but helpful.
